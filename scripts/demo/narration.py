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
    1: "この音の違い、聞こえますか。らてあーとのできは、このすうじゅうびょうのすちーむで、ほぼ決まります。",
    2: "かたちにはなる。でも、りんかくがぼやける。原因はたいてい、そそぐ前のすちーむにあります。"
       "写真にはうつらず、音にしか残りません。しかも、やり方もマシンも人によって違う。"
       "だから、正解を押し付けるのではなく、一緒にそだつこーちを作りました。",
    3: "開始を押して、だいどころに置くだけ。すちーむが終わると、しらせが来ます。"
       "そそぎ終わったら、ぴっちゃーの残りを、いちまいとります。",
    4: "こーちは、音のかたちと写真を見て、みっつだけかえします。原因のこうていをひとつ。"
       "次のいっぱいでなおすてんをひとつ、耳と手でできる言葉で。そして、次のはいで起きるはずの変化をひとつ。"
       "さいてんやくのえーあいが、言いすぎたしんだんを、さしもどします。"
       "けさのいっぱいめは、うずの途中で、うっかり空気を入れていました。",
    5: "続けて、にはいめ。言われたとおりにすると、いっぱいめで空気が入っていた音が消え、あわのまくも、うすくなりました。"
       "こーちのはんていは、ほぼあたり。ただし、続けていれたはいなので、なおしの効果とは言い切れない、とも書いてきます。",
    6: "最初は、えーあいの耳も、しょしんしゃでした。ある日、こーちが自分から書いてきました。"
       "あぷりのはんていが、早すぎる。残っていた音で確かめると、そのとおりでした。"
       "静かなうずの音が、部屋のものおとと同じ大きさだったんです。はんていはなおり、ばーじょんが上がりました。"
       "わたしが耳で教え、えーあいがかたちで気づく。こうして一緒にそだっていきます。",
    7: "まいばん、こーちがその日のはいを、ふりかえります。当たったなおしかたは、あなたのせいかいに。"
       "わたしが教えたことは、こーちの読みより、ゆうせんしておぼえます。そして、よくあさのてーまをひとつ決めます。",
    8: "うずのかいてんほうこうは、音では分かりません。だから、次のはいの結果で確かめます。音は、いえから出しません。",
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
