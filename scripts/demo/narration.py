"""デモ動画の語りを、場面ごとに ElevenLabs の声で音声ファイルにする。

使い方:
  set -a; . ~/.config/latte-coach/env; set +a   # ELEVENLABS_API_KEY を読む（キーはコミットしない）
  uv run --with requests python scripts/demo/narration.py <出力先> [場面番号...]

台本は docs/project/demo.md の「筋」の表と同じ。読み間違えやすい所は、読みを仮名に開いてある。
送るのは台本の文字だけで、練習の音は送らない（decisions.md D21）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

VOICE_ID = "dp4HJlekKt0HZFHL2jQg"  # Ayaka（ElevenLabs のボイスライブラリ）
MODEL_ID = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")

# 表記は demo.md、ここは読み上げ用（数字や「杯」を仮名に開く）
SCENES = {
    1: "この音の違い、聞こえますか。ラテアートの出来は、この数十秒のスチームで、ほぼ決まります。",
    2: "形にはなる。でも、輪郭がぼやける。原因はたいてい、注ぐ前のスチームにあります。"
       "写真には写らず、音にしか残りません。しかも、やり方もマシンも人によって違う。"
       "だから、正解を押し付けるのではなく、一緒に育つコーチを作りました。",
    3: "開始を押して、台所に置くだけ。スチームが終わると知らせが来ます。"
       "注ぎ終わったら、ピッチャーの残りを、いちまい撮ります。",
    4: "コーチは、音の形と写真を見て、みっつだけ返します。原因の工程をひとつ。"
       "次のいっぱいで直す点をひとつ、耳と手でできる言葉で。そして、次の杯で起きるはずの変化をひとつ。"
       "採点役のエーアイが、言いすぎた診断を差し戻します。"
       "今朝のいっぱいめは、渦の途中で、うっかり空気を入れていました。",
    5: "続けて、にはいめ。言われたとおりにすると、あの山が消え、泡の膜も薄くなりました。"
       "コーチの判定は、当たり寄り。ただし、続けて淹れた杯なので、直しの効果とは言い切れない、とも書いてきます。",
    6: "最初は、エーアイの耳も初心者でした。ある日、コーチが自分から書いてきました。"
       "アプリの判定が早すぎる。残っていた音で確かめると、そのとおりでした。"
       "静かな渦の音が、部屋の物音と同じ大きさだったんです。判定は直り、版が上がりました。"
       "私が耳で教え、エーアイが形で気づく。こうして一緒に育っていきます。",
    7: "毎晩、コーチがその日の杯を振り返ります。当たった直し方は、あなたの正解に。"
       "私が教えたことは、コーチの読みより優先して覚えます。そして、翌朝のテーマをひとつ決めます。",
    8: "渦の回転方向は、音では分かりません。だから、次の杯の結果で確かめます。音は、家から出しません。",
}


def synth(text: str, out: Path) -> None:
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        json={
            "text": text,
            "model_id": MODEL_ID,
            "language_code": "ja",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "speed": 1.0},
        },
        timeout=120,
    )
    if r.status_code != 200:
        sys.exit(f"失敗 {r.status_code}: {r.text[:300]}")
    out.write_bytes(r.content)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    outdir = Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    nums = [int(a) for a in sys.argv[2:]] or sorted(SCENES)
    for n in nums:
        path = outdir / f"scene{n}.mp3"
        synth(SCENES[n], path)
        print(path)


if __name__ == "__main__":
    main()
