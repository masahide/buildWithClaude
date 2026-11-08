"""コーチの記憶（Managed Agents のメモリストア）。ユーザーと一緒に育つための置き場（decisions.md D18）。

| パス | 中身 | 書く人 |
| --- | --- | --- |
| /profile.md | この人のスチームのやり方と機材 | サーバーが最初の中身を入れる。夜の振り返りが追記 |
| /reading.md | この人の音の読み方。コーチが学んだこと | 夜の振り返り |
| /rules.md | あなたの正解（当たった直し方） | 夜の振り返り |
| /tendencies.md | 杯をまたいだ癖 | 夜の振り返り |
| /today.md | 今日のテーマ1つ | 夜の振り返り |
| /cups/YYYY-MM-DD.md | その日の杯の記録 | 夜の振り返り |
| /params.md | 判定の版の履歴（提案・承認・見送り） | サーバー（承認・見送りのとき） |

1杯ごとの診断は読むだけ（read_only）、夜の振り返りが書く（read_write）。
"""

from __future__ import annotations

import json
from pathlib import Path

import anthropic

IDS = Path(__file__).parent / "data" / "memory_ids.json"
STORE_NAME = "steam-coach"

# 最初の中身。11-03〜11-07 に本人と一緒に分かったことから書く（docs/log）
SEED = {
    "/profile.md": """# この人のスチーム

- 家庭用のエスプレッソマシン。スチームは 50〜60 秒ほど（マシンによって 15〜60 秒と幅がある）
- 手順: 空だし → ノズルをミルクに入れて蒸気を出す → 始めに甲高い「キュルルル」→ 泡入れ（ジュルジュル）
  → 渦に入って静かな撹拌 → 止める間際に「キュルキュル」→ 止める → 拭く → 空だし
- 泡が足りないと思うと、一度渦に入ってから追加で泡入れすることがある
- 撹拌中に「チリチリ」と少し空気が入ってしまうことがある
- マシン、ノズルの穴数、ピッチャー容量、ミルクの銘柄と量、目指す泡の仕上がり: まだ聞いていない
""",
    "/reading.md": """# この人の音の読み方（コーチが学んだこと）

- 泡入れは音量が細かく上下する区間として拾っている。始めのキュルルルは泡入れに含めない
- 追加の泡入れ（re_air_count / re_air_sec）は、11-05 の杯で「泡が少し多かった」と一緒に出た。泡の量につながる候補
- 撹拌中のチリチリは今の特徴量では拾えていない（4〜8 kHz の短い山として現れることは分かっている）
- 11-06 より前の杯は判定の方法が違うので、数値を今の杯と直接比べない
- 長さの違うマシンでも形は同じ割合で現れる（キュルルル約 8%、渦への位置 約 38%）。秒より割合で比べるほうが安全
""",
    "/rules.md": "# あなたの正解\n\n（まだない。当たった直し方を夜の振り返りが書き足す）\n",
    "/tendencies.md": "# 杯をまたいだ癖\n\n（まだない）\n",
    "/today.md": "# 今日のテーマ\n\n（まだない。夜の振り返りが書く）\n",
}

READABLE = ["/today.md", "/rules.md", "/reading.md", "/tendencies.md", "/profile.md"]


def store_id(client: anthropic.Anthropic) -> str:
    if IDS.exists():
        return json.loads(IDS.read_text())["memory_store_id"]
    store = client.beta.memory_stores.create(
        name=STORE_NAME,
        description="家庭でミルクスチームを練習する1人のための記憶。この人のやり方と機材、この人の音の読み方、"
                    "当たった直し方（あなたの正解）、杯をまたいだ癖、今日のテーマ、日ごとの杯の記録。",
    )
    for path, content in SEED.items():
        client.beta.memory_stores.memories.create(store.id, path=path, content=content)
    IDS.parent.mkdir(parents=True, exist_ok=True)
    IDS.write_text(json.dumps({"memory_store_id": store.id}, indent=2))
    return store.id


def resource(client: anthropic.Anthropic, access: str, instructions: str) -> dict:
    return {"type": "memory_store", "memory_store_id": store_id(client), "access": access, "instructions": instructions}


def teach(client: anthropic.Anthropic, text: str, when: str) -> None:
    """本人がコーチに教えたことを /reading.md に日付つきで書き足す。コーチは次の診断から読む"""
    sid = store_id(client)
    current = next(m for m in client.beta.memory_stores.memories.list(sid, path_prefix="/", view="full")
                   if m.type == "memory" and m.path == "/reading.md")
    head = "## 本人から教わったこと"
    body = current.content.rstrip()
    if head not in body:
        body += f"\n\n{head}\n（コーチの読みより優先する。コーチの読みと食い違えば、こちらが正しい）"
    body += f"\n- {when}: {text.strip()}\n"
    client.beta.memory_stores.memories.update(
        current.id, memory_store_id=sid, content=body,
        precondition={"type": "content_sha256", "content_sha256": current.content_sha256})


def note_params(client: anthropic.Anthropic, line: str) -> None:
    """判定の版の履歴（提案・承認・見送り）を /params.md に書き足す。コーチは次から読む"""
    sid = store_id(client)
    existing = next((m for m in client.beta.memory_stores.memories.list(sid, path_prefix="/", view="full")
                     if m.type == "memory" and m.path == "/params.md"), None)
    if existing is None:
        client.beta.memory_stores.memories.create(
            sid, path="/params.md",
            content="# 判定の版の履歴\n\nアプリの判定の閾値は、コーチが提案し、本人が承認したときだけ変わる。"
                    "版が違う杯どうしは、数値を直接比べない。\n\n" + f"- {line}\n")
        return
    client.beta.memory_stores.memories.update(
        existing.id, memory_store_id=sid, content=existing.content.rstrip() + f"\n- {line}\n",
        precondition={"type": "content_sha256", "content_sha256": existing.content_sha256})


def read_all(client: anthropic.Anthropic) -> dict[str, str]:
    """アプリに見せる分を読む（パス → 中身）"""
    sid = store_id(client)
    out = {}
    for m in client.beta.memory_stores.memories.list(sid, path_prefix="/", view="full"):
        if m.type == "memory" and m.path in READABLE:
            out[m.path] = m.content
    return out
