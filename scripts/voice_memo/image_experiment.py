# /// script
# requires-python = ">=3.12"
# dependencies = ["anthropic", "numpy", "matplotlib"]
# ///
"""音の画像だけを Claude に見せて、スチームの境を判定させる実験（開発用）。

答えの線や印を入れない画像を描き、Messages API に1回ずつ見せて、境・泡入れの区間・チリチリ・ゴボゴボの時刻を答えさせる。
正解ラベル（本人の耳）とアプリの判定と比べ、精度・回ごとのばらつき・時間を見る。音声ファイルそのものは送らない。

  set -a; . ~/.config/latte-coach/env; set +a
  uv run scripts/voice_memo/image_experiment.py notes/private/recordings/2026-11-05-a.wav \\
      --judge notes/private/pictures/2026-11-05-a.json --labels notes/private/recordings/2026-11-05-a.labels.json --runs 3

条件: spectrogram（スペクトログラムだけ）/ bands（4帯域の音量グラフだけ）/ both（両方）。
画像と結果は notes/private/experiments/（git 管理外）に保存する。
"""

from __future__ import annotations

import argparse
import base64
import json
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic
import matplotlib
import numpy as np
from pydantic import BaseModel, Field

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "notes" / "private" / "experiments"
MODEL = "claude-opus-5-5"


class Answer(BaseModel):
    purge_start: Optional[float] = Field(description="空だしの始まり（秒）")
    purge_end: Optional[float] = Field(description="空だしの終わり（秒）")
    steam_start: float = Field(description="ミルクの中で蒸気を出し始めた時刻（キュルルルの始まり）")
    squeal_end: float = Field(description="始めのキュルルルの終わり")
    air_segments: list[list[float]] = Field(description="泡入れ（ジュルジュル）の区間 [始まり, 終わり] の一覧。追加の泡入れも含める")
    transition: float = Field(description="最後の泡入れから渦（静かな撹拌）に移った時刻")
    chiri_times: list[float] = Field(description="撹拌中のチリチリ（ごく高い音の短い音）の時刻")
    burst_times: list[float] = Field(description="撹拌中のゴボゴボ（中くらいの高さの音が急に大きくなる短い音）の時刻")
    steam_end: float = Field(description="蒸気を止めた時刻")
    evidence: str = Field(description="判断の根拠を短く。迷った点があれば書く")


PROMPT = """添付は、家庭のエスプレッソマシンでミルクをスチームしたときの音を描いた画像です（{what}）。横軸は録音の先頭からの秒です。

録音の流れ: 録音開始 → 空だし（ノズルの水抜き。1秒ほどの大きな音）→ 準備の物音 → ノズルをミルクに入れて蒸気を出す
→ 始めに甲高い「キュルルル」→ 泡入れの「ジュルジュル」→ 渦に入って静かになる撹拌 → 止める間際に「キュルキュル」→ 止める。
泡入れは1回とは限りません。一度静かになってから、追加で泡入れすることがあります。撹拌中に、ごく高い音の短い「チリチリ」（少し空気が入る音）や、
中くらいの高さの「ゴボゴボ」が入ることがあります。録音はスチームを止めた直後に終わります。

画像から読み取れる範囲で、各時刻を 0.1 秒単位で答えてください。目盛りをよく見て、推測で埋めないでください。"""

WHAT = {
    "spectrogram": "スペクトログラム。縦軸は周波数、明るいほど大きい音",
    "bands": "4つの帯域（低 50-400 Hz、中 400-2000 Hz、高 2-4 kHz、最高 4-8 kHz）の音量の時間変化。縦軸は背景音に対する dB",
    "both": "1枚目はスペクトログラム（縦軸は周波数、明るいほど大きい音）、2枚目は4つの帯域（低 50-400 Hz、中 400-2000 Hz、高 2-4 kHz、最高 4-8 kHz）の音量の時間変化",
}


def load(wav: Path):
    w = wave.open(str(wav))
    sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    hop, n = int(sr * 0.1), 4096
    frames = [np.pad(x[i:i + n], (0, max(0, n - len(x[i:i + n])))) * np.hanning(n) for i in range(0, len(x) - hop + 1, hop)]
    P = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    return P, np.fft.rfftfreq(n, 1 / sr), np.arange(len(frames)) * 0.1


def axis_ticks(ax, t_end: float) -> None:
    ax.set_xticks(np.arange(0, t_end + 0.01, 5))
    ax.set_xticks(np.arange(0, t_end + 0.01, 1), minor=True)
    ax.grid(which="major", axis="x", color="white", alpha=.6, lw=1)
    ax.grid(which="minor", axis="x", color="white", alpha=.25, lw=.5)
    ax.set_xlim(0, t_end)
    ax.set_xlabel("seconds")


def draw(P, f, t, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    bg = np.median(P[:30], axis=0) + 1e-12
    paths = {}
    fig, ax = plt.subplots(figsize=(19.5, 6), dpi=80)
    m = (f >= 50) & (f <= 8000)
    ax.pcolormesh(t, f[m], 10 * np.log10(P[:, m] / bg[m] + 1e-12).T, shading="auto", cmap="magma", vmin=-5, vmax=35)
    ax.set_ylabel("Hz")
    axis_ticks(ax, t[-1])
    plt.tight_layout(); paths["spectrogram"] = out_dir / "spectrogram.png"; plt.savefig(paths["spectrogram"]); plt.close()

    fig, ax = plt.subplots(figsize=(19.5, 6), dpi=80)
    for lo, hi, name, style in [(50, 400, "low 50-400", "-"), (400, 2000, "mid 400-2k", "--"),
                                (2000, 4000, "high 2-4k", "-."), (4000, 8000, "top 4-8k", ":")]:
        sel = (f >= lo) & (f < hi)
        v = P[:, sel].sum(1)
        ax.plot(t, 10 * np.log10(v / np.median(v[:30]) + 1e-12), style, lw=1.4, label=name)
    ax.set_ylabel("dB over background"); ax.legend(loc="upper right", ncol=4)
    axis_ticks(ax, t[-1]); ax.grid(which="major", axis="x", color="gray"); ax.grid(which="minor", axis="x", color="lightgray")
    ax.grid(axis="y", alpha=.3)
    plt.tight_layout(); paths["bands"] = out_dir / "bands.png"; plt.savefig(paths["bands"]); plt.close()
    return paths


def image_block(path: Path) -> dict:
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                       "data": base64.standard_b64encode(path.read_bytes()).decode()}}


def ask(client: anthropic.Anthropic, condition: str, images: dict[str, Path], run: int) -> dict:
    blocks = [image_block(images["spectrogram"]), image_block(images["bands"])] if condition == "both" \
        else [image_block(images[condition])]
    t0 = time.monotonic()
    resp = client.messages.parse(
        model=MODEL, max_tokens=16000,
        thinking={"type": "adaptive"}, output_config={"effort": "high"},
        messages=[{"role": "user", "content": blocks + [{"type": "text", "text": PROMPT.format(what=WHAT[condition])}]}],
        output_format=Answer,
    )
    return {"condition": condition, "run": run, "elapsed_sec": round(time.monotonic() - t0, 1),
            "stop_reason": resp.stop_reason, "answer": resp.parsed_output.model_dump() if resp.parsed_output else None,
            "usage": {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens}}


def near(times: list[float], spans: list[list[float]], tol: float = 0.7) -> tuple[int, int]:
    """正解の区間（±tol）に入った検出の数と、どれにも入らなかった検出の数"""
    hit = sum(any(s - tol <= x <= e + tol for s, e in spans) for x in times)
    return hit, len(times) - hit


def score(a: dict, L: dict) -> dict:
    segs = sorted(a["air_segments"])
    s = {k: round(a[k] - L[k], 1) for k in ("steam_start", "transition", "steam_end") if k in L and a.get(k) is not None}
    if "purge" in L and a.get("purge_start") is not None:
        s["purge_start"] = round(a["purge_start"] - L["purge"][0], 1)
    s["air_count"] = len(segs)
    if segs:
        s["air1_end"] = round(segs[0][1] - L["air1_end"], 1)
    if len(segs) >= 2 and "re_air" in L:
        s["re_air_start"] = round(segs[1][0] - L["re_air"][0], 1)
        s["re_air_end"] = round(segs[1][1] - L["re_air"][1], 1)
    if "chiri" in L:
        hit, extra = near(a["chiri_times"], L["chiri"])
        found = sum(any(sp[0] - 0.7 <= x <= sp[1] + 0.7 for x in a["chiri_times"]) for sp in L["chiri"])
        s["chiri"] = f"{found}/{len(L['chiri'])} found, {extra} extra"
    return s


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("wav", type=Path)
    p.add_argument("--judge", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--condition", action="append", choices=list(WHAT))
    args = p.parse_args()

    L = json.loads(args.labels.read_text())
    J = json.loads(args.judge.read_text())
    stamp = f"{datetime.now():%Y%m%d-%H%M%S}-images"
    images = draw(*load(args.wav), OUT_DIR / stamp)
    client = anthropic.Anthropic()
    jobs = [(c, r) for c in (args.condition or list(WHAT)) for r in range(1, args.runs + 1)]
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        results = list(pool.map(lambda j: ask(client, j[0], images, j[1]), jobs))
    for r in results:
        r["score"] = score(r["answer"], L) if r["answer"] else None

    f = J.get("features") or {}
    print("app:", {k: round(v - L[k], 1) for k, v in J.get("marks", {}).items() if k in L},
          "air1", f.get("first_air_sec"), "re_air", f.get("re_air_count"), f.get("re_air_sec"))
    for r in results:
        a = r["answer"] or {}
        print(f"\n[{r['condition']} #{r['run']}] {r['elapsed_sec']} s  tokens {r['usage']}")
        print("  air:", a.get("air_segments"), " chiri:", a.get("chiri_times"), " bursts:", a.get("burst_times"))
        print("  score:", r["score"])
    out = OUT_DIR / f"{stamp}.json"
    out.write_text(json.dumps({"labels": L, "results": results}, ensure_ascii=False, indent=2))
    print("\n保存:", out)


if __name__ == "__main__":
    main()
