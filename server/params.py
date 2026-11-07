"""iPhone の判定の閾値を版つきで持つ（decisions.md D20）。

コーチ（夜の振り返り）が変更を提案し、本人がアプリで承認したときだけ新しい版になる。
アプリは練習の開始時に今の版を取りに来て判定に使い、杯ごとに版を記録する。版が違う杯どうしは数値を直接比べない。

  data/params/v1.json, v2.json ...  各版の閾値と、なぜ変えたか
  data/params/current.json          今の版の番号
  data/params/proposal.json         承認待ちの提案（なければ無い）
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

DIR = Path(__file__).parent / "data" / "params"

# アプリの FeatureThresholds の既定値（ios/LatteCoach/Audio/FeatureExtractor.swift）と同じ。名前・意味・許す範囲
SPEC: dict[str, dict] = {
    "onset_db": {"default": 10, "min": 4, "max": 20, "means": "1秒平均の音量が背景よりこの dB を超えた状態が onset_sustain_sec 続いたらスチームの始まり"},
    "onset_sustain_sec": {"default": 2, "min": 1, "max": 4, "means": "始まりとみなすのに要る継続時間。空だし（約1秒）を除くため"},
    "stay_db": {"default": 1.5, "min": 0.5, "max": 6, "means": "1秒平均の音量がこれを end_quiet_sec 下回ったらスチームの終わり。渦の静かな撹拌でも途切れない値にする"},
    "end_quiet_sec": {"default": 2, "min": 1, "max": 5, "means": "終わりとみなすのに要る静かな時間"},
    "min_steam_sec": {"default": 8, "min": 4, "max": 20, "means": "これより短い区間はスチームとみなさない"},
    "squeal_high_ratio": {"default": 0.9, "min": 0.6, "max": 0.98, "means": "始めのキュルルル: 区間の先頭で高域（2-8kHz）の割合がこれ以上の間"},
    "air_gap_fraction": {"default": 0.03, "min": 0.01, "max": 0.1, "means": "泡入れの途中の途切れをつなぐ長さ（スチームの長さに対する割合。下限 0.7 秒・上限 1.5 秒）"},
    "min_air_fraction": {"default": 0.05, "min": 0.02, "max": 0.15, "means": "これより短い揺れの大きい区間は泡入れに数えない（ゴボゴボとみなす）。スチームの長さに対する割合（下限 1.5 秒・上限 2.5 秒）"},
    "end_squeal_fraction": {"default": 0.06, "min": 0.02, "max": 0.15, "means": "止める間際のキュルキュルとして、撹拌の値から除く末尾の長さ（割合。下限 1 秒・上限 3 秒）"},
    "burst_over_median_db": {"default": 6, "min": 3, "max": 15, "means": "撹拌中の中域がその中央値よりこの dB 以上大きくなった立ち上がりをゴボゴボと数える"},
}


def _path(v: int) -> Path:
    return DIR / f"v{v}.json"


def current() -> dict:
    """{"version": n, "values": {...}, "reason": ..., "applied_at": ...}"""
    DIR.mkdir(parents=True, exist_ok=True)
    cur = DIR / "current.json"
    if not cur.exists():
        v1 = {"version": 1, "values": {k: s["default"] for k, s in SPEC.items()},
              "reason": "11-05 のボイスメモと本人の耳で合わせた最初の値（D15〜D17）", "applied_at": datetime.now().isoformat()}
        _path(1).write_text(json.dumps(v1, ensure_ascii=False, indent=2))
        cur.write_text(json.dumps({"version": 1}))
    return json.loads(_path(json.loads(cur.read_text())["version"]).read_text())


def describe() -> str:
    """コーチに見せる今の版と、各値の意味と範囲"""
    c = current()
    lines = [f"今の判定の版: v{c['version']}（{c.get('reason', '')}）"]
    for k, s in SPEC.items():
        lines.append(f"- {k} = {c['values'][k]}（範囲 {s['min']}〜{s['max']}）: {s['means']}")
    return "\n".join(lines)


def validate(changes: dict) -> dict:
    """知らない名前は捨て、範囲の外は範囲に収める"""
    out = {}
    for k, v in (changes or {}).items():
        if k in SPEC and isinstance(v, (int, float)):
            out[k] = max(SPEC[k]["min"], min(SPEC[k]["max"], float(v)))
    return out


def propose(changes: dict, reason: str, evidence: str, source: str) -> Optional[dict]:
    clean = validate(changes)
    cur = current()["values"]
    clean = {k: v for k, v in clean.items() if abs(v - float(cur[k])) > 1e-9}
    if not clean:
        return None
    p = {"changes": clean, "before": {k: cur[k] for k in clean}, "reason": reason, "evidence": evidence,
         "source": source, "proposed_at": datetime.now().isoformat()}
    # 承認する前に、保存してある杯の音で測り直して見せる（D21）
    try:
        import rejudge
        rows = rejudge.compare(dict(cur), {**cur, **clean})
        p["replay"] = rows
        p["replay_summary"] = rejudge.summary(rows)
    except Exception as e:  # 測り直せなくても提案は出す
        p["replay_summary"] = f"過去の杯で測り直せなかった: {e}"
    (DIR / "proposal.json").write_text(json.dumps(p, ensure_ascii=False, indent=2))
    return p


def proposal() -> Optional[dict]:
    p = DIR / "proposal.json"
    return json.loads(p.read_text()) if p.exists() else None


def decide(accept: bool) -> dict:
    """承認なら新しい版を作る。どちらでも提案は片づけ、結果を返す"""
    p = proposal()
    if not p:
        raise ValueError("承認待ちの提案がない")
    (DIR / "proposal.json").unlink()
    if not accept:
        return {"accepted": False, "proposal": p}
    cur = current()
    new = {"version": cur["version"] + 1, "values": {**cur["values"], **p["changes"]},
           "reason": p["reason"], "evidence": p["evidence"], "applied_at": datetime.now().isoformat(), "approved_by": "本人"}
    _path(new["version"]).write_text(json.dumps(new, ensure_ascii=False, indent=2))
    (DIR / "current.json").write_text(json.dumps({"version": new["version"]}))
    return {"accepted": True, "proposal": p, "version": new["version"]}
