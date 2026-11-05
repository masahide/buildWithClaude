"""コーチ本体の呼び出し。1杯ぶんの特徴量と写真から、原因の工程1つ・直す点1つ・予測1つを返す。

方式は環境変数 COACH_BACKEND で切り替える（どちらにするかは待ち時間の計測で決める。decisions.md 未決）。
  managed  : Managed Agents のセッション＋Outcomes（採点役が差し戻す。既定。decisions.md D13）
  messages : Messages API を1回呼ぶ（待ち時間が長すぎるときの戻し先）
  fake     : API を呼ばず固定の診断を返す（アプリとの通し確認用）
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Literal, Optional

import anthropic
from pydantic import BaseModel, Field

MODEL = os.environ.get("COACH_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("COACH_EFFORT", "medium")

SYSTEM = """あなたは家庭でラテアートを練習する人のための、ミルクスチームのコーチです。
1杯ぶんの音響特徴量（端末で計算した相対値）と、注ぎ終わった後のピッチャーの残りの写真1枚から診断します。

- 原因の工程を「エア入れ」「撹拌」のどちらか1つだけ選ぶ
- 次の1杯で直す点を1つだけ返す。耳・手・時間で実行できる言葉にする（cm・温度・角度の数値を測らせない）
  例: 「裂く音を今より1秒短く」「ピッチャーを縁側へ寄せる」「沈めるのを今より早く」
- 次の杯で観測できる変化の予測を1つだけ返す（音か、ピッチャーの残りの見た目で確かめられるもの）
- 根拠は今回の特徴量か写真の所見に置く
- 前の杯の診断が渡されたら、その予測が今回当たったかを先に判定して previous_verdict に書く。なければ null
- 注ぎやカップの模様は診断・採点しない。カップが写っていても、ピッチャーの所見の裏付けにだけ使う
- 写真の所見は「泡の大きさ」「泡の固さ」「艶」を各 0〜2 で数値化する
- 音で分からないもの（渦の回転方向、縦横の撹拌のバランス、ノズルの正確な位置と深さ）は観測したかのように書かない

この人のスチームの音の並び: 蒸気を出した直後の甲高い「キュルルル」→ 泡入れの「ジュルジュル」（音量が細かく上下する）
→ 渦に入って静かで滑らかな撹拌 → 止める間際の「キュルキュル」。前後の空だしはスチーム区間に含めない。

特徴量の意味:
- steam_duration_sec: スチーム区間の長さ（秒）。蒸気を出してから止めるまで
- start_squeal_sec: 始めの「キュルルル」の長さ（秒）
- air_phase_ratio: スチーム区間のうち、泡入れ（ジュルジュル）が占める割合。始めのキュルルルは含まない
- transition_at: 泡入れから渦（撹拌）へ移った位置（区間の先頭からの割合）
- stir_stability: 撹拌相の音の滑らかさ（1 に近いほど滑らか。渦が安定している）
- stir_low_band_ratio: 撹拌相の低域の割合。高いとノズルが深すぎる疑い
- burst_count: 撹拌相で中域が急に大きくなった回数（ゴボゴボ）。多いと渦ができていない疑い
- level_over_background_db: 背景音に対する音量。置き場所の目安で、診断の根拠にはしない
判定は本人の録音1本で合わせた暫定値なので、数値は杯どうしの比較として読むこと。11-04 以前の杯は判定の方法が違うため、数値を直接比べない。
"""

RUBRIC = """# 1杯の診断のルーブリック
- 原因の工程が「エア入れ」「撹拌」のちょうど1つである
- 直す点がちょうど1つで、複数の指摘を含まない
- 直す点が耳・手・時間で実行できる。cm・温度・角度の数値の測定を要求しない
- 次の杯で観測できる予測がちょうど1つ付いている
- 根拠が、今回の音響特徴量か写真の所見のどちらかにある
- 前の杯の診断が渡されていれば、その予測の当否を述べている
- 注ぎやカップの模様を診断・採点していない
- 写真の所見（泡の大きさ・泡の固さ・艶）が各 0〜2 の数値で記されている
- 末尾に指定の JSON コードブロックがある
"""


class PhotoScores(BaseModel):
    bubble_size: int = Field(description="泡の大きさ。0=細かい 1=やや粗い 2=大きな泡が目立つ")
    firmness: int = Field(description="泡の固さ。0=流れる 1=やや固い 2=固く乾いている")
    gloss: int = Field(description="艶。0=艶なし 1=少しある 2=塗料のような艶")


class Diagnosis(BaseModel):
    process: Literal["エア入れ", "撹拌"]
    fix: str = Field(description="次の1杯で直す点1つ。耳・手・時間で実行できる言葉")
    prediction: str = Field(description="次の杯で観測できるはずの変化1つ")
    evidence: str = Field(description="根拠。今回の特徴量か写真の所見")
    previous_verdict: Optional[str] = Field(
        default=None, description="前の杯の予測の当否（当たった／外れた＋理由）。前の杯がなければ null"
    )
    photo_scores: Optional[PhotoScores] = None


class CoachError(Exception):
    pass


def _user_content(features: Optional[dict], self_rating: Optional[str], photo: Optional[bytes],
                  previous: Optional[dict]) -> list[dict]:
    parts: list[str] = []
    if previous:
        parts.append(
            "前の杯の記録（この予測が今回当たったかを先に判定する）:\n"
            f"```json\n{json.dumps(previous, ensure_ascii=False, indent=2)}\n```"
        )
    if features:
        parts.append(f"今回の杯の音響特徴量:\n```json\n{json.dumps(features, ensure_ascii=False, indent=2)}\n```")
    else:
        parts.append("今回の杯はスチーム区間を検出できなかった。写真だけで診断する。")
    if self_rating:
        parts.append(f"本人の自己評価: {self_rating}")
    parts.append("写真は添付の1枚（ピッチャーの残り）。" if photo else "写真はない。特徴量だけで診断する。")
    parts.append("診断してください。")

    content: list[dict] = []
    if photo:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg",
                       "data": base64.standard_b64encode(photo).decode()},
        })
    content.append({"type": "text", "text": "\n\n".join(parts)})
    return content


def diagnose(features: Optional[dict], self_rating: Optional[str], photo: Optional[bytes],
             previous: Optional[dict]) -> Diagnosis:
    backend = os.environ.get("COACH_BACKEND", "managed")
    content = _user_content(features, self_rating, photo, previous)
    if backend == "managed":
        return _diagnose_managed(content)
    if backend == "fake":
        time.sleep(2)
        return Diagnosis(
            process="撹拌", fix="ピッチャーを今より縁側へ寄せる",
            prediction="裂く音の後のゴボゴボが消える", evidence="通し確認用の固定の診断",
            previous_verdict="前の杯あり（固定の判定）" if previous else None,
        )
    return _diagnose_messages(content)


def _diagnose_messages(content: list[dict]) -> Diagnosis:
    client = anthropic.Anthropic()
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        system=SYSTEM,
        thinking={"type": "adaptive"},
        output_config={"effort": EFFORT},
        # 安全側の分類器が誤って断ったとき、サーバー側で別モデルに回す
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": content}],
        output_format=Diagnosis,
    )
    if response.stop_reason == "refusal":
        raise CoachError("診断を返せませんでした（refusal）")
    if response.parsed_output is None:
        raise CoachError(f"診断の形式が不正です（stop_reason={response.stop_reason}）")
    return response.parsed_output


# --- Managed Agents ---------------------------------------------------------

MANAGED_IDS = Path(__file__).parent / "data" / "managed_ids.json"
MANAGED_SYSTEM = SYSTEM + """
最後に次の JSON だけを含むコードブロックを出力する:
{"process": "エア入れ|撹拌", "fix": "...", "prediction": "...", "evidence": "...",
 "previous_verdict": "..." または null, "photo_scores": {"bubble_size": 0, "firmness": 0, "gloss": 0}}
"""


def _managed_ids(client: anthropic.Anthropic) -> dict:
    if MANAGED_IDS.exists():
        ids = json.loads(MANAGED_IDS.read_text())
        # プロンプトを変えたら、保存してあるエージェントを新しい版に更新する
        digest = hashlib.sha256(MANAGED_SYSTEM.encode()).hexdigest()
        if ids.get("system_sha256") != digest:
            agent = client.beta.agents.update(ids["agent_id"], version=ids["agent_version"], system=MANAGED_SYSTEM)
            ids.update(agent_version=agent.version, system_sha256=digest)
            MANAGED_IDS.write_text(json.dumps(ids, indent=2))
        return ids
    env = client.beta.environments.create(
        name="latte-coach", config={"type": "cloud", "networking": {"type": "limited"}}
    )
    agent = client.beta.agents.create(
        name="スチームコーチ",
        model=MODEL,
        system=MANAGED_SYSTEM,
        tools=[{
            "type": "agent_toolset_20260401",
            "default_config": {"enabled": True, "permission_policy": {"type": "auto"}},
            "configs": [{"name": "web_fetch", "enabled": False}, {"name": "web_search", "enabled": False}],
        }],
    )
    ids = {"agent_id": agent.id, "agent_version": agent.version, "environment_id": env.id,
           "system_sha256": hashlib.sha256(MANAGED_SYSTEM.encode()).hexdigest()}
    MANAGED_IDS.parent.mkdir(parents=True, exist_ok=True)
    MANAGED_IDS.write_text(json.dumps(ids, indent=2))
    return ids


def _diagnose_managed(content: list[dict]) -> Diagnosis:
    client = anthropic.Anthropic()
    ids = _managed_ids(client)
    session = client.beta.sessions.create(
        agent={"type": "agent", "id": ids["agent_id"], "version": ids["agent_version"]},
        environment_id=ids["environment_id"],
        title="1杯の診断",
    )
    texts: list[str] = []
    with client.beta.sessions.events.stream(session_id=session.id) as stream:
        client.beta.sessions.events.send(session_id=session.id, events=[
            {"type": "user.message", "content": content},
            {"type": "user.define_outcome",
             "description": "上のメッセージの杯について、ルーブリックを満たす診断を1つ返す",
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

    for text in reversed(texts):
        for block in reversed(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)):
            try:
                return Diagnosis.model_validate_json(block)
            except ValueError:
                continue
    raise CoachError(f"診断の JSON が見つかりません（session={session.id}）")
