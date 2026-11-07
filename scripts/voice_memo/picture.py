"""ボイスメモの答え合わせ図を描く（開発用。sound-picture.md A）。

  uv run --with numpy --with matplotlib python scripts/voice_memo/picture.py 録音.wav 判定.json ラベル.json 出力.png [開始秒 終了秒]

上から: スペクトログラム（0.1 秒刻み）、帯域ごとの音量（3帯域＋4〜8 kHz）、音量の揺れ。
縦線: 実線がアプリの判定、破線が本人の耳。図は notes/private/pictures/（git 管理外）に置く。
"""
import json, sys, wave
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["Hiragino Sans", "Hiragino Kaku Gothic ProN", "sans-serif"]
wav, judge, labels, out = sys.argv[1:5]
t0, t1 = (float(sys.argv[5]), float(sys.argv[6])) if len(sys.argv) > 6 else (None, None)

w = wave.open(wav); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
hop, n = int(sr * 0.1), 4096
frames = [np.pad(x[i:i + n], (0, max(0, n - len(x[i:i + n])))) * np.hanning(n) for i in range(0, len(x) - hop + 1, hop)]
P = np.abs(np.fft.rfft(frames, axis=1)) ** 2
f = np.fft.rfftfreq(n, 1 / sr); t = np.arange(len(frames)) * 0.1
bg = np.median(P[:30], axis=0) + 1e-12
S = 10 * np.log10(P / bg + 1e-12)

def band(lo, hi):
    m = (f >= lo) & (f < hi)
    v = P[:, m].sum(1); return 10 * np.log10(v / np.median(v[:30]) + 1e-12)

J = json.load(open(judge)); L = json.load(open(labels))
fig, ax = plt.subplots(3, 1, figsize=(18, 11), sharex=True, gridspec_kw={"height_ratios": [3, 2, 1.2]})
m = (f >= 50) & (f <= 8000)
ax[0].pcolormesh(t, f[m], S[:, m].T, shading="auto", cmap="magma", vmin=-5, vmax=35)
ax[0].set_ylabel("周波数 (Hz)"); ax[0].set_title("スペクトログラム（背景音比 dB、0.1 秒刻み）")
for (lo, hi, name, style) in [(50, 400, "低 50-400", "-"), (400, 2000, "中 400-2k", "--"), (2000, 4000, "高 2-4k", "-."), (4000, 8000, "最高 4-8k（チリチリ）", ":")]:
    ax[1].plot(t, band(lo, hi), style, lw=1.3 if lo != 4000 else 2, label=name)
ax[1].set_ylabel("背景音比 (dB)"); ax[1].legend(loc="upper right", ncol=4); ax[1].grid(alpha=.3)
tot = sum(np.asarray(e) for e in zip(*J["envelope"]))
db = 10 * np.log10(np.maximum(tot, 1e-12))
jit = np.array([db[max(0, i - 5):i + 5].std() for i in range(len(db))])
jit = np.convolve(jit, np.ones(10) / 10, mode="same")
ax[2].plot(np.arange(len(jit)) * 0.1, jit, color="k"); ax[2].set_ylabel("音量の揺れ"); ax[2].grid(alpha=.3)
ax[2].set_xlabel("秒（録音の先頭から）")

def vline(x, text, color, ls):
    for a in ax: a.axvline(x, color=color, ls=ls, lw=1.2)
    ax[0].text(x, 7600, text, color=color, rotation=90, va="top", ha="right", fontsize=10,
               bbox=dict(facecolor="white", alpha=.7, lw=0))

for k, v in J.get("marks", {}).items():
    vline(v, {"steam_start": "アプリ: 始まり", "transition": "アプリ: 渦へ", "steam_end": "アプリ: 終わり"}.get(k, k), "deepskyblue", "-")
ear = {"steam_start": "耳: 蒸気", "air1_end": "耳: 泡入れ終わり", "transition": "耳: 渦へ", "steam_end": "耳: 止めた"}
for k, name in ear.items():
    if k in L: vline(L[k], name, "lime", "--")
for k in ("re_air", "purge"):
    if k in L:
        for a in ax: a.axvspan(*L[k], color="lime" if k == "re_air" else "gray", alpha=.12)
        ax[0].text(L[k][0], 500, "耳: 追加の泡入れ" if k == "re_air" else "空だし", color="white", fontsize=10)
for c in L.get("chiri", []):
    for a in ax: a.axvspan(c[0], c[1], color="yellow", alpha=.18)
    ax[0].text(c[0], 300, "耳: チリチリ", color="yellow", fontsize=10)
if t0 is not None:
    ax[0].set_xlim(t0, t1)
ax[2].set_xticks(np.arange(int(t0 or 0), int(t1 or t[-1]) + 1, 1 if t0 is not None else 5))
plt.tight_layout(); plt.savefig(out, dpi=80)
print(out)
