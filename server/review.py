"""夜の振り返り。その日の杯を読み、コーチの記憶を育てる（decisions.md D18）。

その日の杯（特徴量・自己評価・診断・前の杯の予測の当否・写真の所見）を Managed Agents のセッションに渡し、
メモリストアに書かせる: 当たった直し方は /rules.md へ、外れた読みや本人に教わったことは /reading.md へ、
杯をまたいだ癖は /tendencies.md へ、明日のテーマ1つは /today.md へ、その日の記録は /cups/<日付>.md へ。

  cd server && set -a && . ~/.config/latte-coach/env && set +a
  uv run python review.py            # 今日の杯
  uv run python review.py 2026-11-07 # 日付を指定
サーバーからは POST /review で呼べる。
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

import anthropic

import coach
import memory
import sound_picture

DATA = Path(__file__).parent / "data" / "cups"

RUBRIC = """# 夜の振り返りのルーブリック
- /cups/<日付>.md に、その日の杯ごとの特徴量の要点・自己評価・診断・予測の当否が書かれている
- 予測が当たった直し方が、/rules.md に「状況 → 直し方 → 起きた変化（どの杯で確かめたか）」の形で足されている。当たりがなければ足していない
- /reading.md に、この日に分かった「この人の音の読み方」が足されている。外れた予測があれば、なぜ外れたと考えるかが書かれている
- 杯をまたいだ癖を /tendencies.md に書くときは、2杯以上の数値を引いて述べている
- /today.md が、明日のテーマちょうど1つに書き換えられている。耳・手・時間で実行できる言葉になっている
- 既存の内容を消していない（古くなった記述は「〜と思っていたが」と残して直す）
- /reading.md の「本人から教わったこと」と食い違う読みをしていない。食い違う数値は、本人の言葉を正として扱っている
- 包絡や音の絵を根拠にした記述には、何秒あたりの何を見たかが書かれている
"""


def cups_of(day: date) -> list[dict]:
    cups = []
    for d in sorted(DATA.iterdir()):
        s = json.loads((d / "status.json").read_text())
        if not s.get("received_at", "").startswith(day.isoformat()):
            continue
        m = json.loads((d / "meta.json").read_text())
        cups.append({
            "received_at": s["received_at"], "status": s.get("status"), "elapsed_sec": s.get("elapsed_sec"),
            "self_rating": m.get("self_rating"), "features": m.get("features"), "diagnosis": s.get("diagnosis"),
            "_envelope": m.get("envelope"), "_marks": m.get("marks"), "_dir": str(d),
        })
    return sorted(cups, key=lambda c: c["received_at"])


def run(day: date) -> dict:
    cups = cups_of(day)
    if not cups:
        return {"day": day.isoformat(), "cups": 0, "note": "杯がないので振り返らない"}
    client = anthropic.Anthropic()
    ids = coach._managed_ids(client)
    # 杯ごとの包絡（0.1 秒ごとの帯域エネルギー）と音の絵を作業用の環境に置く。コーチは自分で解析してよい
    resources = []
    for i, c in enumerate(cups, start=1):
        name = f"{i:02d}_{c['received_at'][11:16].replace(':', '')}"
        env, marks, cup_dir = c.pop("_envelope"), c.pop("_marks"), Path(c.pop("_dir"))
        c["files"] = {}
        if env:
            data = json.dumps({"frame_sec": 0.1, "bands": ["low 50-400Hz", "mid 400-2000Hz", "high 2000-8000Hz", "top 4000-8000Hz"][:len(env[0])],
                               "unit": "背景音（練習開始直後の数秒の中央値）に対する比（線形）", "marks_sec": marks, "envelope": env})
            f = client.files.upload(file=(f"{name}.json", data.encode(), "application/json"))
            resources.append({"type": "file", "file_id": f.id, "mount_path": f"/workspace/cups/{name}.json"})
            c["files"]["envelope"] = f"/workspace/cups/{name}.json"
            png_path = cup_dir / "sound.png"
            png = png_path.read_bytes() if png_path.exists() else sound_picture.draw(env, marks, name)
            if png:
                f = client.files.upload(file=(f"{name}.png", png, "image/png"))
                resources.append({"type": "file", "file_id": f.id, "mount_path": f"/workspace/cups/{name}.png"})
                c["files"]["picture"] = f"/workspace/cups/{name}.png"
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": ids["agent_id"], "version": ids["agent_version"]},
        environment_id=ids["environment_id"],
        title=f"夜の振り返り {day.isoformat()}",
        resources=[memory.resource(client, "read_write",
                                   "この人の記憶。振り返りの前に全部読み、学んだことを書き足す。")] + resources,
    )
    text = (
        f"今日（{day.isoformat()}）は、1杯ごとの診断ではなく夜の振り返りをします。今日の杯は {len(cups)} 杯でした。\n"
        f"```json\n{json.dumps(cups, ensure_ascii=False, indent=2)}\n```\n"
        "各杯の files に、帯域ごとの音量の包絡（JSON）と音の絵（PNG）の置き場所がある（11-07 より前の杯にはない）。"
        "アプリの特徴量は、今わかっている範囲の切り取り方でしかない。必要なら Python で包絡を解析し、絵を見て、"
        "杯どうしの形を比べ、数値に出ていない出来事（泡入れの収まり方、チリチリやゴボゴボの位置、低域の上がり方など）に気づいたら "
        "/reading.md に、何秒あたりの何を見たかと一緒に書いてください。アプリの判定の境（marks_sec）が形と食い違って見えたら、それも書いてください。\n"
        "メモリストアの記憶を読んでから、ルーブリックを満たすように書き足してください。"
        "あなたもこの人も、スチームの初心者から一緒に育っている途中です。分からないことは分からないと書き、"
        "次に確かめることとして残してください。"
    )
    texts: list[str] = []
    with client.beta.sessions.events.stream(session_id=session.id) as stream:
        client.beta.sessions.events.send(session_id=session.id, events=[
            {"type": "user.message", "content": [{"type": "text", "text": text}]},
            {"type": "user.define_outcome", "description": "今日の杯を振り返り、記憶を育てる",
             "rubric": {"type": "text", "content": RUBRIC}, "max_iterations": 3},
        ])
        for event in stream:
            if event.type == "agent.message":
                texts.extend(b.text for b in event.content if b.type == "text")
            elif event.type in ("agent.tool_use", "agent.mcp_tool_use") and \
                    getattr(event, "evaluated_permission", None) == "ask":
                client.beta.sessions.events.send(session_id=session.id, events=[
                    {"type": "user.tool_confirmation", "tool_use_id": event.id, "result": "deny"}])
            elif event.type == "session.status_idle" and event.stop_reason.type != "requires_action":
                break
            elif event.type == "session.status_terminated":
                break
    return {"day": day.isoformat(), "cups": len(cups), "session_id": session.id,
            "finished_at": datetime.now().isoformat(), "summary": texts[-1] if texts else ""}


if __name__ == "__main__":
    day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    print(json.dumps(run(day), ensure_ascii=False, indent=2))
