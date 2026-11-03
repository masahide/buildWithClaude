# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic"]
# ///
"""診断の待ち時間を測る（plan.md 確認項目2）。

ピッチャーの残りの写真1枚と仮の特徴量で「1杯の診断」を回し、方式ごとの待ち時間を比べる。

  managed  : Managed Agents のセッション＋Outcomes（採点役が差し戻す）
  plain    : Managed Agents のセッション、Outcomes なし
  messages : Messages API を1回呼ぶだけ（比較用）

使い方:
  export ANTHROPIC_API_KEY=...   # コミットしない
  uv run scripts/latency/measure.py PHOTO.jpg --mode managed --mode messages

エージェントと環境は初回だけ作り、ID を scripts/latency/.ids.json（git 管理外）に保存して使い回す。
結果は scripts/latency/results/ に JSON で残す（git 管理外。要点は docs/log に転記する）。
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import time
from datetime import datetime
from pathlib import Path

import anthropic

HERE = Path(__file__).parent
IDS_PATH = HERE / ".ids.json"
RESULTS_DIR = HERE / "results"
MODEL = "claude-opus-5-5"

SYSTEM = """あなたは家庭でラテアートを練習する人のための、ミルクスチームのコーチです。
1杯ぶんの音響特徴量（端末で計算した相対値）と、注ぎ終わった後のピッチャーの残りの写真1枚から診断します。

- 原因の工程を「エア入れ」「撹拌」のどちらか1つだけ選ぶ
- 次の1杯で直す点を1つだけ返す。耳・手・時間で実行できる言葉にする（cm や温度の測定を求めない）
- 次の杯で観測できる変化の予測を1つだけ返す
- 根拠は今回の特徴量か写真の所見に置く
- 注ぎやカップの模様は診断・採点しない
- 写真の所見は「泡の大きさ」「泡の固さ」「艶」を各 0〜2 で数値化する

最後に次の JSON だけを含むコードブロックを出力する:
{"process": "エア入れ|撹拌", "fix": "...", "prediction": "...", "evidence": "...",
 "photo_scores": {"bubble_size": 0, "firmness": 0, "gloss": 0}}
"""

RUBRIC = """# 1杯の診断のルーブリック
- 原因の工程が「エア入れ」「撹拌」のちょうど1つである
- 直す点がちょうど1つで、複数の指摘を含まない
- 直す点が耳・手・時間で実行できる。cm・温度・角度の数値の測定を要求しない
- 次の杯で観測できる予測がちょうど1つ付いている
- 根拠が、今回の音響特徴量か写真の所見のどちらかにある
- 注ぎやカップの模様を診断・採点していない
- 写真の所見（泡の大きさ・泡の固さ・艶）が各 0〜2 の数値で記されている
- 末尾に指定の JSON コードブロックがある
"""

# 実データが揃うまでの仮の特徴量。--features で実測値の JSON を渡せる
DEFAULT_FEATURES = {
    "steam_duration_sec": 32.4,
    "air_phase_ratio": 0.38,
    "transition_at": 0.38,
    "stir_stability": 0.71,
    "stir_low_band_ratio": 0.22,
    "burst_count": 4,
    "self_rating": "泡が多すぎた",
}


def load_ids() -> dict:
    return json.loads(IDS_PATH.read_text()) if IDS_PATH.exists() else {}


def ensure_agent(client: anthropic.Anthropic) -> dict:
    ids = load_ids()
    if "agent_id" in ids and "environment_id" in ids:
        return ids
    env = client.beta.environments.create(
        name="latte-coach-latency",
        config={"type": "cloud", "networking": {"type": "limited"}},
    )
    agent = client.beta.agents.create(
        name="スチームコーチ（待ち時間計測）",
        model=MODEL,
        system=SYSTEM,
        tools=[
            {
                "type": "agent_toolset_20260401",
                "default_config": {"enabled": True, "permission_policy": {"type": "auto"}},
                "configs": [
                    {"name": "web_fetch", "enabled": False},
                    {"name": "web_search", "enabled": False},
                ],
            }
        ],
    )
    ids = {"agent_id": agent.id, "agent_version": agent.version, "environment_id": env.id}
    IDS_PATH.write_text(json.dumps(ids, indent=2))
    print(f"作成: agent={agent.id} env={env.id}")
    return ids


def user_text(features: dict, photo_note: str) -> str:
    return (
        "今回の杯の音響特徴量（相対値）:\n"
        f"```json\n{json.dumps(features, ensure_ascii=False, indent=2)}\n```\n"
        f"{photo_note}\n診断してください。"
    )


def image_block(photo: Path) -> dict:
    media_type = mimetypes.guess_type(photo.name)[0] or "image/jpeg"
    data = base64.standard_b64encode(photo.read_bytes()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}


def run_managed(client: anthropic.Anthropic, photo: Path, features: dict, with_outcome: bool) -> dict:
    ids = ensure_agent(client)
    marks: dict[str, float] = {}
    t0 = time.monotonic()

    session = client.beta.sessions.create(
        agent={"type": "agent", "id": ids["agent_id"], "version": ids["agent_version"]},
        environment_id=ids["environment_id"],
        title=f"latency {datetime.now():%Y-%m-%d %H:%M}",
    )
    marks["session_created"] = time.monotonic() - t0

    msg = {
        "type": "user.message",
        "content": [image_block(photo), {"type": "text", "text": user_text(features, "写真は添付の1枚。")}],
    }
    events = [msg]
    if with_outcome:
        events.append(
            {
                "type": "user.define_outcome",
                "description": "上のメッセージの杯について、ルーブリックを満たす診断を1つ返す",
                "rubric": {"type": "text", "content": RUBRIC},
                "max_iterations": 3,
            }
        )

    texts: list[str] = []
    evaluations: list[dict] = []
    with client.beta.sessions.events.stream(session_id=session.id) as stream:
        t_send = time.monotonic()
        client.beta.sessions.events.send(session_id=session.id, events=events)
        marks["sent"] = time.monotonic() - t0

        for event in stream:
            now = time.monotonic() - t0
            if event.type == "session.status_running":
                marks.setdefault("first_running", now)
            elif event.type == "span.model_request_start":
                marks.setdefault("first_model_request", now)
            elif event.type == "agent.message":
                marks.setdefault("first_agent_message", now)
                marks["last_agent_message"] = now
                texts.extend(b.text for b in event.content if b.type == "text")
            elif event.type == "span.outcome_evaluation_end":
                evaluations.append(
                    {"iteration": event.iteration, "result": event.result, "explanation": event.explanation, "at": now}
                )
            elif (event.type in ("agent.tool_use", "agent.mcp_tool_use")) and getattr(
                event, "evaluated_permission", None
            ) == "ask":
                # 無人で回すので保留中のツール呼び出しは拒否する
                client.beta.sessions.events.send(
                    session_id=session.id,
                    events=[{"type": "user.tool_confirmation", "tool_use_id": event.id, "result": "deny"}],
                )
            elif event.type == "session.status_idle":
                if event.stop_reason.type != "requires_action":
                    marks["idle"] = now
                    break
            elif event.type == "session.status_terminated":
                marks["terminated"] = now
                break

    done = marks.get("idle", marks.get("terminated", time.monotonic() - t0))
    retrieved = client.beta.sessions.retrieve(session_id=session.id)
    return {
        "mode": "managed" if with_outcome else "plain",
        "session_id": session.id,
        "marks_sec": {k: round(v, 2) for k, v in marks.items()},
        "send_to_done_sec": round(done - (t_send - t0), 2),
        "total_sec": round(done, 2),
        "evaluations": evaluations,
        "usage": json.loads(retrieved.usage.model_dump_json()) if getattr(retrieved, "usage", None) else None,
        "final_text": texts[-1] if texts else "",
    }


def run_messages(client: anthropic.Anthropic, photo: Path, features: dict) -> dict:
    t0 = time.monotonic()
    first_token = None
    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        messages=[
            {
                "role": "user",
                "content": [image_block(photo), {"type": "text", "text": user_text(features, "写真は添付の1枚。")}],
            }
        ],
    ) as stream:
        for event in stream:
            if first_token is None and event.type == "content_block_delta":
                first_token = time.monotonic() - t0
        message = stream.get_final_message()
    total = time.monotonic() - t0
    return {
        "mode": "messages",
        "stop_reason": message.stop_reason,
        "first_token_sec": round(first_token or total, 2),
        "total_sec": round(total, 2),
        "usage": json.loads(message.usage.model_dump_json()),
        "final_text": "".join(b.text for b in message.content if b.type == "text"),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("photo", type=Path, help="ピッチャーの残りの写真（jpg/png）")
    p.add_argument("--mode", action="append", choices=["managed", "plain", "messages"])
    p.add_argument("--features", type=Path, help="特徴量の JSON（省略時は仮の値）")
    args = p.parse_args()

    features = json.loads(args.features.read_text()) if args.features else DEFAULT_FEATURES
    modes = args.mode or ["managed", "messages"]
    client = anthropic.Anthropic()
    RESULTS_DIR.mkdir(exist_ok=True)

    for mode in modes:
        print(f"\n=== {mode} ===")
        if mode == "messages":
            result = run_messages(client, args.photo, features)
        else:
            result = run_managed(client, args.photo, features, with_outcome=(mode == "managed"))
        out = RESULTS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{mode}.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        summary = {k: v for k, v in result.items() if k not in ("final_text", "usage")}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print("--- 最終回答 ---\n" + result["final_text"])
        print(f"保存: {out}")


if __name__ == "__main__":
    main()
