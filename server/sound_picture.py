"""杯ごとの音の絵（sound-picture.md B）。アプリが送る包絡（0.1 秒ごとの帯域エネルギー、背景音比）から描く。

横軸は蒸気を出してからの秒。縦軸は全杯で固定して、杯どうしを並べて比べられるようにする。
上から: 帯域ごとの音量（低・中・高・最高 4–8 kHz）、音量の揺れ。縦線はアプリの判定の境。
コーチ（毎杯の診断と夜の振り返り）に見せ、README とデモにも使う。
"""

from __future__ import annotations

import io
from typing import Optional

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams["font.family"] = ["Hiragino Sans", "Hiragino Kaku Gothic ProN", "sans-serif"]

BANDS = [("低 50-400Hz", "-", "#1f77b4"), ("中 400-2kHz", "--", "#ff7f0e"),
         ("高 2-8kHz", "-.", "#2ca02c"), ("最高 4-8kHz（チリチリ）", ":", "#d62728")]
MARK_NAMES = {"steam_start": "始まり", "squeal_end": "キュルルル終わり", "transition": "渦へ", "steam_end": "止めた"}


def _db(x: np.ndarray) -> np.ndarray:
    return 10 * np.log10(np.maximum(x, 1e-6))


def draw(envelope: list[list[float]], marks: Optional[dict] = None, title: str = "") -> Optional[bytes]:
    """PNG のバイト列を返す。スチーム区間が見つからなければ None"""
    if not envelope:
        return None
    E = np.asarray(envelope, dtype=float)
    total = E[:, :3].sum(1)
    t = np.arange(len(E)) * 0.1
    if marks and "steam_start" in marks and "steam_end" in marks:
        s0, s1 = marks["steam_start"], marks["steam_end"]
    else:  # 境のない杯は、音量が背景より +10 dB を超える最初と最後で大まかに切る
        loud = np.where(_db(total) > 10)[0]
        if len(loud) == 0:
            return None
        s0, s1 = loud[0] * 0.1, loud[-1] * 0.1
        marks = None
    lo, hi = max(0.0, s0 - 5), min(t[-1], s1 + 5)
    sel = (t >= lo) & (t <= hi)
    x = t[sel] - s0  # 蒸気を出してからの秒

    fig, ax = plt.subplots(2, 1, figsize=(15, 8), dpi=100, sharex=True, gridspec_kw={"height_ratios": [3, 1.2]})
    for i, (name, style, color) in enumerate(BANDS):
        if i < E.shape[1]:
            ax[0].plot(x, _db(E[sel, i]), style, color=color, lw=1.8 if i == 3 else 1.2, label=name)
    ax[0].set_ylim(-15, 50)
    ax[0].set_ylabel("背景音比 (dB)")
    ax[0].legend(loc="upper right", ncol=4, fontsize=11)
    db_total = _db(total)
    jit = np.array([db_total[max(0, i - 5):i + 5].std() for i in range(len(db_total))])
    jit = np.convolve(jit, np.ones(10) / 10, mode="same")
    ax[1].plot(x, jit[sel], color="black", lw=1.4)
    ax[1].set_ylim(0, 12)
    ax[1].set_ylabel("音量の揺れ")
    ax[1].set_xlabel("蒸気を出してからの秒")
    end = max(75.0, (hi - s0))
    for a in ax:
        a.set_xlim(-5, end)
        a.set_xticks(np.arange(-5, end + 0.1, 5))
        a.grid(alpha=.35)
    if marks:
        for k, v in marks.items():
            if k in MARK_NAMES:
                for a in ax:
                    a.axvline(v - s0, color="purple", lw=1.2)
                ax[0].text(v - s0, 48, MARK_NAMES[k], color="purple", rotation=90, va="top", ha="right", fontsize=11,
                           bbox=dict(facecolor="white", alpha=.75, lw=0))
    if title:
        ax[0].set_title(title, fontsize=13)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
