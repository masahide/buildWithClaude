# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic"]
# ///
"""ボイスメモから作った数値データを Managed Agents のエージェントに渡し、スチームの境を解析させる実験（開発用）。

エージェントは作業用の環境で自分でコードを書き、図を描いて確かめながら境の時刻を答える。
同じ入力で何回か回し、正解ラベル・アプリの判定とのずれと、回ごとのばらつきを見る。
音声ファイルそのものは送らない。送るのは judge（3帯域の包絡）と spectrum.py（64 帯域）の出力だけ。

  set -a; . ~/.config/latte-coach/env; set +a
  uv run scripts/voice_memo/agent_experiment.py notes/private/pictures/2026-11-05-a \\
      --labels notes/private/recordings/2026-11-05-a.labels.json --runs 3

<prefix>.json（judge の出力）と <prefix>.spectrum.json（spectrum.py の出力）を使う。
結果は notes/private/experiments/（git 管理外）に保存する。
"""

from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "notes" / "private" / "experiments"
IDS = OUT_DIR / "agent_ids.json"
MODEL = "claude-opus-5-5"
KEYS = ["purge_start", "purge_end", "steam_start", "squeal_end", "transition", "end_squeal_start", "steam_end"]

SYSTEM = """あなたは音響データの解析者です。渡された数値データを、作業用の環境で Python を使って解析します。
推測で答えず、データから確かめた値だけを答えてください。図を描いたら、画像ファイルを開いて自分の目で確かめてかまいません。"""

CONDITIONS = {
    "envelope": {
        "file": "{prefix}.json",
        "describe": "`envelope` は 0.1 秒ごとの3帯域（低 50-400 Hz、中 400-2000 Hz、高 2000-8000 Hz）のエネルギーで、"
                    "録音の先頭3秒の中央値（背景音）に対する比（線形）です。`marks` と `features` は無視してください。",
    },
    "spectrum": {
        "file": "{prefix}.spectrum.json",
        "describe": "`spectrum_db` は 0.1 秒ごとの 64 帯域（50 Hz〜8 kHz を対数で等分、境は `band_edges_hz`）のエネルギーで、"
                    "帯域ごとに録音の先頭3秒の中央値（背景音）に対する dB です。",
    },
}

TASK = """/workspace/input.json は、家庭のエスプレッソマシンでミルクをスチームしたときの音から作ったデータです（音声そのものはありません）。
{describe}

録音の流れ: 録音開始 → 空だし（ノズルの水抜き。1秒ほどの大きな音）→ 準備の物音 → ノズルをミルクに入れて蒸気を出す
→ 始めに甲高い「キュルルル」→ 泡入れの「ジュルジュル」→ 渦に入って静かになる撹拌 → 止める間際に「キュルキュル」→ 止める。
録音はスチームを止めた直後に終わります。

次の時刻を、録音の先頭からの秒（0.1 秒単位）で推定してください。
- purge_start, purge_end: 空だしの始まりと終わり
- steam_start: ミルクの中で蒸気を出し始めた時刻（キュルルルの始まり）
- squeal_end: 始めのキュルルルの終わり
- transition: 泡入れ（ジュルジュル）から渦（静かな撹拌）に移った時刻
- end_squeal_start: 止める間際のキュルキュルの始まり
- steam_end: 蒸気を止めた時刻
- burst_times: 撹拌中のゴボゴボ（中域が急に大きくなる短い音）の時刻の一覧

最後に、次の形の JSON コードブロックを1つだけ出力してください。
{{"purge_start": 0.0, "purge_end": 0.0, "steam_start": 0.0, "squeal_end": 0.0, "transition": 0.0,
 "end_squeal_start": 0.0, "steam_end": 0.0, "burst_times": [], "evidence": {{"<キー>": "何を見てそう判断したか"}}}}
"""


def ensure_agent(client: anthropic.Anthropic) -> dict:
    if IDS.exists():
        return json.loads(IDS.read_text())
    env = client.beta.environments.create(
        name="steam-sound-analysis",
        config={"type": "cloud", "networking": {"type": "limited", "allow_package_managers": True}},
    )
    agent = client.beta.agents.create(
        name="スチーム音の解析（実験）",
        model=MODEL,
        system=SYSTEM,
        tools=[{
            "type": "agent_toolset_20260401",
            "default_config": {"enabled": True, "permission_policy": {"type": "auto"}},
            "configs": [{"name": "web_fetch", "enabled": False}, {"name": "web_search", "enabled": False}],
        }],
    )
    ids = {"agent_id": agent.id, "agent_version": agent.version, "environment_id": env.id}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    IDS.write_text(json.dumps(ids, indent=2))
    return ids


def run_once(client: anthropic.Anthropic, ids: dict, file_id: str, condition: str, run: int) -> dict:
    t0 = time.monotonic()
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": ids["agent_id"], "version": ids["agent_version"]},
        environment_id=ids["environment_id"],
        title=f"steam analysis {condition} #{run}",
        resources=[{"type": "file", "file_id": file_id, "mount_path": "/workspace/input.json"}],
    )
    texts: list[str] = []
    tool_uses = 0
    with client.beta.sessions.events.stream(session_id=session.id) as stream:
        client.beta.sessions.events.send(session_id=session.id, events=[{
            "type": "user.message",
            "content": [{"type": "text", "text": TASK.format(describe=CONDITIONS[condition]["describe"])}],
        }])
        for event in stream:
            if event.type == "agent.message":
                texts.extend(b.text for b in event.content if b.type == "text")
            elif event.type in ("agent.tool_use", "agent.mcp_tool_use"):
                tool_uses += 1
                if getattr(event, "evaluated_permission", None) == "ask":
                    client.beta.sessions.events.send(session_id=session.id, events=[
                        {"type": "user.tool_confirmation", "tool_use_id": event.id, "result": "deny"}])
            elif event.type == "session.status_idle" and event.stop_reason.type != "requires_action":
                break
            elif event.type == "session.status_terminated":
                break
    answer = None
    for text in reversed(texts):
        blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
        if blocks:
            try:
                answer = json.loads(blocks[-1])
                break
            except json.JSONDecodeError:
                continue
    return {"condition": condition, "run": run, "session_id": session.id, "elapsed_sec": round(time.monotonic() - t0, 1),
            "tool_uses": tool_uses, "answer": answer, "final_text": texts[-1] if texts else ""}


def score(answer: dict | None, labels: dict) -> dict:
    if not answer:
        return {}
    truth = dict(labels)
    if "purge" in truth:
        truth["purge_start"], truth["purge_end"] = truth.pop("purge")
    return {k: round(float(answer[k]) - float(truth[k]), 1)
            for k in KEYS if k in truth and isinstance(answer.get(k), (int, float))}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("prefix", help="notes/private/pictures/<名前>（.json と .spectrum.json の前まで）")
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--condition", action="append", choices=list(CONDITIONS))
    args = p.parse_args()

    labels = json.loads(args.labels.read_text())
    labels.pop("note", None)
    app_marks = json.loads(Path(f"{args.prefix}.json").read_text()).get("marks", {})
    conditions = args.condition or list(CONDITIONS)
    client = anthropic.Anthropic()
    ids = ensure_agent(client)

    file_ids = {}
    for c in conditions:
        with open(CONDITIONS[c]["file"].format(prefix=args.prefix), "rb") as f:
            file_ids[c] = client.files.upload(file=("input.json", f, "application/json")).id

    jobs = [(c, r) for c in conditions for r in range(1, args.runs + 1)]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        results = list(pool.map(lambda j: run_once(client, ids, file_ids[j[0]], *j), jobs))
    for r in results:
        r["error_sec"] = score(r["answer"], labels)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{Path(args.prefix).name}.json"
    out.write_text(json.dumps({"labels": labels, "app_marks": app_marks, "results": results}, ensure_ascii=False, indent=2))

    print("app marks:", app_marks)
    print("app error:", {k: round(app_marks[k] - labels[k], 1) for k in app_marks if k in labels})
    for r in results:
        a = r["answer"] or {}
        print(f"\n[{r['condition']} #{r['run']}] {r['elapsed_sec']} s, tools {r['tool_uses']}, bursts {len(a.get('burst_times') or [])}")
        print("  answer:", {k: a.get(k) for k in KEYS})
        print("  error :", r["error_sec"])
    print("\n保存:", out)


if __name__ == "__main__":
    main()
