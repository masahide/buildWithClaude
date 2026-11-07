"""保存した杯の音に、アプリと同じ判定を当て直す（decisions.md D21）。

判定の計算はアプリの Swift（ios/LatteCoach/Audio/FeatureExtractor.swift）の1か所だけに置く。
この Mac で scripts/voice_memo/judge と一緒にコンパイルしたコマンドを使い、Python に書き写さない。
コーチの閾値の提案（D20）を、本人が承認する前に過去の杯で確かめるのに使う。
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(__file__).parent / "data" / "bin" / "judge"
SOURCES = [ROOT / "ios/LatteCoach/Audio/FeatureExtractor.swift", ROOT / "scripts/voice_memo/judge/main.swift"]
DATA = Path(__file__).parent / "data" / "cups"
KEYS = ["steam_duration_sec", "start_squeal_sec", "first_air_sec", "re_air_count", "re_air_sec", "transition_at", "burst_count"]


def _binary() -> Path:
    newest = max(p.stat().st_mtime for p in SOURCES)
    if not BIN.exists() or BIN.stat().st_mtime < newest:
        BIN.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", *map(str, SOURCES), "-o", str(BIN)], check=True, capture_output=True)
    return BIN


def judge(audio: Path, values: dict, background: float | None = None) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(values, f)
    args = [str(_binary()), str(audio), f.name] + ([str(background)] if background else [])
    out = subprocess.run(args, check=True, capture_output=True, timeout=120)
    d = json.loads(out.stdout)
    return {"features": d.get("features"), "marks": d.get("marks")}


def compare(before: dict, after: dict, limit: int = 10) -> list[dict]:
    """音のある直近の杯（最大 limit 杯）を、今の値と提案の値で測り直して並べる"""
    cups = sorted((d for d in DATA.iterdir() if (d / "audio.wav").exists()), key=lambda d: (d / "status.json").stat().st_mtime)
    rows = []
    for d in cups[-limit:]:
        received = json.loads((d / "status.json").read_text()).get("received_at", "")[:16]
        bg = json.loads((d / "meta.json").read_text()).get("background")
        a, b = judge(d / "audio.wav", before, bg), judge(d / "audio.wav", after, bg)
        fa, fb = a["features"] or {}, b["features"] or {}
        rows.append({"cup": received, "before": {k: fa.get(k) for k in KEYS}, "after": {k: fb.get(k) for k in KEYS}})
    return rows


def summary(rows: list[dict]) -> str:
    """本人に見せる短い表（変わった値だけ）"""
    if not rows:
        return "音のある杯がまだないので、過去の杯では試せていない"
    lines = []
    for r in rows:
        diffs = [f"{k} {r['before'][k]}→{r['after'][k]}" for k in KEYS if r["before"].get(k) != r["after"].get(k)]
        lines.append(f"{r['cup']}: " + ("、".join(diffs) if diffs else "変化なし"))
    return "\n".join(lines)
