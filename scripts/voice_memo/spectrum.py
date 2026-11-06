"""ボイスメモから細かいスペクトログラム（64 帯域、0.1 秒刻み、背景音比 dB）を JSON で出す（開発用）。

時間方向は 0.1 秒より細かくしない（音声に戻せる細かさにしない。sound-picture.md A の扱い）。
  uv run --with numpy python scripts/voice_memo/spectrum.py 録音.wav > 録音.spectrum.json
WAV は afconvert -f WAVE -d LEI16@48000 -c 1 で作る（wave は浮動小数点の WAV を読めない）。
"""
import json, sys, wave
import numpy as np

w = wave.open(sys.argv[1])
sr = w.getframerate()
raw = w.readframes(w.getnframes())
x = np.frombuffer(raw, dtype=np.float32 if w.getsampwidth() == 4 else np.int16).astype(np.float64)
if w.getsampwidth() == 2:
    x /= 32768
hop, n = int(sr * 0.1), 4096
win = np.hanning(n)
frames = [np.pad(x[i:i + n], (0, max(0, n - len(x[i:i + n])))) * win for i in range(0, len(x) - hop + 1, hop)]
power = np.abs(np.fft.rfft(frames, axis=1)) ** 2
freqs = np.fft.rfftfreq(n, 1 / sr)
edges = np.geomspace(50, 8000, 65)
bands = np.stack([power[:, (freqs >= lo) & (freqs < hi)].sum(1) for lo, hi in zip(edges[:-1], edges[1:])], axis=1)
bg = np.median(bands[:30], axis=0) + 1e-12  # アプリと同じく先頭3秒
db = 10 * np.log10(bands / bg + 1e-12)
json.dump({
    "frame_sec": 0.1,
    "band_edges_hz": [round(float(e), 1) for e in edges],
    "unit": "dB over each band's background (median of the first 3 s)",
    "spectrum_db": [[round(float(v), 1) for v in row] for row in db],
}, sys.stdout)
