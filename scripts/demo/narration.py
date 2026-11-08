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
MODEL_ID = os.environ.get("ELEVENLABS_MODEL", "eleven_v4")

# 表記は demo.md、ここは読み上げ用。11-08 に本人が聞いて、読み間違えた漢字と、
# 伸ばし棒の抜けたカタカナ語を仮名に開いた（モデルは eleven_v4 が良かった）
SCENES = {
    # 11-08 夕方に流れを組み直した版（docs/project/demo.md の「筋」）。2 と 5 は前の版の声をそのまま使う
    "1": "家で、らてあーとを練習しています。でも、ひとりだと、しっぱいした理由が分かりません。",
    "2": "かたちにはなる。でも、りんかくがぼやける。原因はたいてい、そそぐ前のすちーむにあります。"
         "写真にはうつらず、音にしか残りません。しかも、やり方もマシンも人によって違う。"
         "だから、正解を押し付けるのではなく、一緒にそだつこーちを作りました。",
    "3a": "けさのいっかいめです。開始を押して、だいどころに置くだけ。",
    "3b": "すちーむが終わると、しらせが来ます。そそぎ終わったら、ぴっちゃーの残りを、いちまいとって送ります。",
    "3c": "いち、にふんで、くろーどのこーちから、返事がとどきます。原因のこうていをひとつ。"
          "次のいっかいでなおすてんをひとつ、耳と手でできる言葉で。そして、次にいれたときに起きるはずの変化をひとつ。",
    "4": "けさは、うずの途中で、うっかり空気を入れていました。続けて、にかいめ。"
         "言われたとおりにすると、空気が入っていた音が消え、あわのまくも、うすくなりました。"
         "こーちのはんていは、ほぼあたり。ただし、続けていれたので、言い切れない、とも書いてきます。",
    "5": "最初は、えーあいの耳も、しょしんしゃでした。ある日、こーちが自分から書いてきました。"
         "あぷりのはんていが、早すぎる。残っていた音で確かめると、そのとおりでした。"
         "静かなうずの音が、部屋のものおとと同じ大きさだったんです。はんていはなおり、ばーじょんが上がりました。"
         "わたしが耳で教え、えーあいがかたちで気づく。こうして一緒にそだっていきます。",
    "6": "しくみです。あいふぉんのあぷりが音を聞き、じたくのまっくに送ります。音は、いえから出しません。"
         "くろーどには、音の数値と絵、写真だけを渡します。まいかいのしんだんでは、さいてんやくのえーあいが、"
         "言いすぎた返事を、さしもどします。まいばんのふりかえりで、教わったことを、記憶に書き足していきます。",
    "7": "らてあーとの正解は、人によって違います。だから、あなたの音から、一緒に正解を見つけていく。"
         "えーあいも、わたしも、しょしんしゃからのすたーとです。",
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
    nums = sys.argv[2:] or list(SCENES)
    for n in nums:
        path = outdir / f"scene{n}.mp3"
        synth(SCENES[n], path)
        print(path)


if __name__ == "__main__":
    main()
