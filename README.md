# ラテアートAIコーチ

**AI もユーザーも初心者から始まり、一緒に育つ、ミルクスチームのコーチ。**

家でラテアートを練習する人のための iPhone アプリと、Claude のコーチ。「開始」を押してスマホを台所に置き、いつもどおりスチームするだけで、1杯ごとに次の3つが届く。

- 原因の工程1つ（エア入れ／撹拌）
- 次の1杯で直す点1つ（耳・手・時間で実行できる言葉）
- 次の杯で起きるはずの変化1つ

次の杯で、その予測が当たったかを確かめる。当たった直し方は「あなたの正解」として溜まる。コーチの音の読み方も、杯を重ね、本人に教わるたびに育っていく。

[Built with Claude: Japan 2026](https://cerebralvalley.ai/events/~/e/built-with-claude-japan2026) への応募作品（テーマ1「あなたにしかない深さを。」）。

## 何に困っているか

ラテアートの出来はミルクのスチームで大半が決まる。それなのに、スチームの正解は熟練者の耳と手の中にしかない。完成した模様を写真で採点するアプリはある。しかし失敗の原因はスチームにあり、写真には写らず音にしか残らない。家で一人で練習すると、失敗しても原因がエア入れか撹拌か分からず、同じ失敗を繰り返す。

## なぜ「一緒に育つ」なのか

スチームのやり方は人によって違う。マシンによって音の質も長さも違い、家庭用でも 15 秒で終わるものから 60 秒かかるものまである。2杯続けて淹れれば、2杯目はマシンの勢いが弱まって長くなる。「誰のどんなスチームでも、音だけで正しく採点する」判定器は作れない（[decisions.md D18](docs/project/decisions.md)）。

そこで、他人と比べて採点するのではなく、**その人の杯どうしを比べ、仮説を立てて次の杯で確かめる**コーチにした（[D7](docs/project/decisions.md)）。最初はコーチも、その人の音の正解を知らない。

| | ユーザーが育つ | コーチが育つ |
| --- | --- | --- |
| 毎杯 | 直す点を1つ試し、自分の耳で確かめる | 予測を立て、次の杯で当否を確かめる。音の絵を見て、アプリの判定が怪しければそう書く |
| 毎晩 | 翌朝、今日のテーマを1つ受け取る | その日の杯を振り返り、当たった直し方を「あなたの正解」に、分かったことを「この人の音の読み方」に書き足す。判定の閾値を変えたほうがよければ提案する |
| ときどき | 「ここは追加の泡入れだった」とコーチに教える。コーチの閾値の提案を、過去の杯で試した結果を見て承認する | 教わったことを、自分の読みより優先する |

### 実際に起きたこと

このループは、作っている途中に本当に回った（[docs/project/timeline.md](docs/project/timeline.md)）。

1. 最初の判定は、作り物の音で決めた「初心者の耳」だった。実際の 40〜60 秒のスチームを 14 秒で切っていた
2. 本人の練習をボイスメモで録り、スペクトログラムにして一緒に見た。本人が「ここは泡入れ、27〜32 秒は追加の泡入れ、ここがチリチリ」と耳で教えた。判定は耳と ±0.4 秒で一致するまで育った（[D15〜D17](docs/project/decisions.md)）
3. 11-07 の杯で、コーチが音の絵（スペクトログラム）を見て、自分から書いてきた。「アプリの『止めた』の線が早すぎる。音は約 62 秒まで続き、止める間際のキュルキュルもある。『始まり』は空だしを拾った可能性がある」。サーバーに残った音で確かめると、そのとおりだった。渦の静かな撹拌が部屋の物音と同じ大きさになっていた。判定を「高い音と低い音の差」で見るように直し、判定の版を v2 に上げた（[D22](docs/project/decisions.md)）

AI が音の形から自分の判定の誤りに気づき、人が音で確かめ、判定が直った。これがこのプロダクトの「深さ」の作り方である。

## 仕組み

```
iPhone（台所に置く）                自宅の Mac（サーバー）                         Claude
 マイク ─→ 0.1秒ごとの帯域の音量 ─┐
         （判定・特徴量）          ├─→ 音・特徴量・写真を保存 ─→ 今の判定の版で測り直す
 練習の音（全部、48kHz）──────────┘      音の絵（スペクトログラム）を描く
 ピッチャーの残りの写真 1枚                      │
                                                 ├─→ 毎杯の診断（Managed Agents＋Outcomes）
                                                 │     数値・音の絵・写真・前の杯・記憶 → 原因1つ・直す点1つ・予測1つ
                                                 └─→ 毎晩の振り返り（Managed Agents）
                                                       その日の包絡と絵を自分で解析 → 記憶（メモリストア）を育てる
                                                       → 閾値の提案 → 本人がアプリで承認
```

| 部品 | 役割 |
| --- | --- |
| iOS アプリ（[ios/](ios/)、SwiftUI） | バックグラウンドで録音し、0.1 秒ごとの帯域の音量からスチーム区間・始めのキュルルル・泡入れ（追加の泡入れも別に）・渦への境・ゴボゴボを判定する。練習の音を全部サーバーに送る。診断・今日のテーマ・あなたの正解・コーチが学んだことを表示し、コーチに教え、閾値の提案を承認する |
| サーバー（[server/](server/)、FastAPI） | 自宅の Mac で動く。API キーを持つ。音から測り直し（アプリと同じ Swift の判定をこの Mac でコンパイルして使う）、音の絵を描き、コーチを呼ぶ。判定の閾値を版つきで持つ |
| コーチ（Claude Managed Agents） | 1杯ごとの診断（Outcomes の採点役が「1点だけ・耳と手と時間で実行できる・予測つき」を確かめる）。毎晩の振り返り（その日の包絡と音の絵を作業用の環境で自分で解析し、メモリストアに書く） |
| 記憶（メモリストア） | この人のやり方と機材、この人の音の読み方、あなたの正解、杯をまたいだ癖、今日のテーマ、判定の版の履歴、本人から教わったこと |

## Claude の使い方

- **Managed Agents のセッションで毎杯を診断する。** 待ち時間を測って決めた（約 1〜2 分、[D13](docs/project/decisions.md)）
- **Outcomes で返答を絞る。** 採点役が「原因は1つ、直す点は1つで耳・手・時間の言葉、次の杯で観測できる予測つき」を満たさない診断を差し戻す
- **画像で音の形を読ませる。** 特徴量の数値だけでなく、今回と前の杯の音の絵（スペクトログラム＋帯域の音量＋揺れ）を渡す。数値を正とし、絵は数値に出ない形を読む補助。判定の線が絵と食い違えば `judgment_doubt` に書かせる（[D19](docs/project/decisions.md)）。ピッチャーの残りの写真も見る
- **メモリストアで杯をまたぐ。** 1杯ごとの診断は読むだけ、夜の振り返りが書く（[D18](docs/project/decisions.md)）
- **作業用の環境で自分で解析させる。** 夜の振り返りでは、その日の包絡のデータを渡し、Python で杯どうしの形を比べさせる
- **判定の閾値を提案させ、人が承認する。** 提案はアプリに出て、本人が承認する。サーバーは、保存した音で直近の杯を測り直した結果を提案に添える（アプリにはまだ表示していない。[D20](docs/project/decisions.md)）

使っていないもの: 音声そのもの（Claude は音を直接聞けない。渡すのは数値と画像）。画像だけでの判定（実験で、アプリの数値の判定より劣ると分かった。[log/2026-11-07.md](docs/log/2026-11-07.md)）。

## 音とプライバシー

生の音声は家の外に出さない（[D21](docs/project/decisions.md)）。

- iPhone は練習の音を開始から終了まで全部、自宅の Mac のサーバーに送る。サーバーで何度でもスチームを切り出し直し、判定を当て直し、絵を描き直せるようにするため
- 音声は GitHub にも Anthropic（Claude）にも送らない。Claude に渡すのは、音から作った数値と画像、ピッチャーの写真だけ
- サーバーを自宅の外（クラウド）に移すときは、この約束を見直す

## 音で分からないこと、限界

- **動作そのものは聞こえない。** 渦の回転方向、縦横の撹拌のバランス、ノズルの正確な位置と深さは分からない。分かるのは結果としての音（[D9](docs/project/decisions.md)）。だから動作を当てるのではなく、症状から原因の工程を推定し、次の杯の結果で確かめる
- **確かめたのは本人1人・家庭用マシン1台・十数杯。** 他の人のやり方、他のマシン（特に 15 秒ほどで終わるもの）では確かめていない。録音を縮めた実験では全体の形は割合で保たれたが、2回の泡入れの間のような細かい出来事はつぶれた（[log/2026-11-07.md](docs/log/2026-11-07.md)）
- **撹拌中のチリチリ（少し空気が入る音）は数えていない。** 4〜8 kHz の短い山として現れることは分かっていて、帯域のデータは送っている
- **判定の閾値は暫定。** 判定の版が上がると、前の版の杯と数値を直接比べられない。コーチには版を伝え、比べないようにさせている
- **無料の Apple ID で開発している。** アプリは7日ごとに入れ直しが要り、リモートのプッシュ通知は使っていない（[D12](docs/project/decisions.md)）

## リポジトリの構成

```
ios/                     iPhone アプリ（SwiftUI、XcodeGen の project.yml から生成）
  LatteCoach/Audio/        録音、0.1 秒ごとの帯域の音量、スチームの区間と工程の判定（FeatureExtractor.swift）
  LatteCoach/Practice/     練習の開始から終了まで、杯の区切り、通知、ピッチャーの写真
  LatteCoach/Coach/        サーバーへの送信と、診断・記憶の取得
  LatteCoach/Views/        杯の一覧と診断、「コーチと一緒に育つ」、コーチに教える
  LatteCoachTests/         実際の音の並びに合わせた合成音で、判定を確かめるテスト
server/                  自宅の Mac で動くサーバー（FastAPI）
  app.py                   エンドポイント
  coach.py                 毎杯の診断（Managed Agents＋Outcomes）
  review.py                夜の振り返り
  memory.py                メモリストア（コーチの記憶）
  params.py                判定の閾値と版、コーチの提案の承認
  rejudge.py               保存した音を今の版の判定で測り直す
  sound_picture.py         音の絵（スペクトログラムと帯域の音量）を描く
scripts/                 開発用の道具と実験（下の「開発用の道具」）
docs/project/            設計・判断・計画・デモの台本
docs/log/                日々の観測と検証の記録
```

## セットアップ

必要なもの: Mac（Xcode 27 以降）、iPhone、[uv](https://docs.astral.sh/uv/)、[XcodeGen](https://github.com/yonaskolb/XcodeGen)、Anthropic の API キー。有償の Apple Developer Program は不要。

### サーバー

```sh
mkdir -p ~/.config/latte-coach
printf 'ANTHROPIC_API_KEY=%s\n' '<あなたのキー>' > ~/.config/latte-coach/env && chmod 600 ~/.config/latte-coach/env  # コミットしない
cd server
set -a; . ~/.config/latte-coach/env; set +a
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

- 初回の診断で、Managed Agents のエージェント・環境・メモリストアが作られ、ID が `server/data/`（git 管理外）に保存される。杯の記録と音声も `server/data/` に残る
- `COACH_BACKEND`: `managed`（既定。Managed Agents＋Outcomes）、`messages`（Messages API を1回。速いが採点役なし）、`fake`（API を呼ばない。通しの確認用）
- 夜の振り返り: `curl -X POST "localhost:8000/review?day=2026-11-07"`、または `uv run python review.py 2026-11-07`
- 過去の杯の測り直しは、`ios/LatteCoach/Audio/FeatureExtractor.swift` と `scripts/voice_memo/judge/` を `swiftc` でコンパイルして使う（自動）

### iOS アプリ

```sh
cd ios
cp Config/Local.xcconfig.example Config/Local.xcconfig   # Team ID・バンドル ID・サーバー URL を書く
xcodegen
open LatteCoach.xcodeproj
```

サーバーの URL は、同じ Wi-Fi にある Mac を `http:/$()/<Mac の名前>.local:8000` の形で書く（xcconfig では `//` がコメントになるため）。

### 開発用の道具

| 道具 | 用途 |
| --- | --- |
| `scripts/voice_memo/judge/` | ボイスメモにアプリと同じ判定を当て、包絡・判定の境・特徴量を出す |
| `scripts/voice_memo/picture.py` | 音の形・アプリの判定の境・本人の耳の境を1枚に重ねた答え合わせ図を描く |
| `scripts/voice_memo/agent_experiment.py` | Managed Agents に音のデータを解析させ、境を答えさせる実験 |
| `scripts/voice_memo/image_experiment.py` | 音の画像だけを見せて境を判定させる実験 |
| `scripts/latency/measure.py` | 診断の待ち時間を方式ごとに測る |

## 開発過程での Claude Code の使い方

このリポジトリは、本人と Claude Code の対話で作った。コードを書かせるだけでなく、次のことに使った。

- **設計を言葉にして残す。** 決めたことと捨てたことを、日付と理由とともに [decisions.md](docs/project/decisions.md)（D1〜D22）に書かせた。本人の発言（「人によってやり方が違う」「情報を削っても後でよいことはない」）が、設計の転換点として記録されている
- **実際の音を一緒に見る。** ボイスメモをスペクトログラムにして Claude Code が読み、本人が耳で答える往復で判定を作り直した。作り物の音に合わせて実際の録音を悪くした変更は、その場で戻した（[log/2026-11-07.md](docs/log/2026-11-07.md)）
- **仮説を実験で確かめる。** 「AI エージェントに音を解析させたら」「画像だけで判定させたら」「音を間引いて送ったら」を、それぞれ実験して数字で判断した（[docs/log/](docs/log/)）
- **引き継ぎ。** 作業の区切りごとに [status.md](docs/project/status.md) を更新し、別のセッションや別の Claude が続きから始められるようにした

## 次にやること

- 他の人・他のマシン（特に短いスチーム）の録音で判定を確かめる。練習仲間やカフェの新人教育へ広げる
- 撹拌中のチリチリを数える
- 音の絵の描き方を、コーチ自身が変えられるようにする
- アプリで自分の音の絵を見られるようにし、耳と形を結びつける
- 「音と結果の写真で工程を診断し、次の1回で検証する」仕組みを、他の伝承的な手技に広げる

## ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [docs/project/status.md](docs/project/status.md) | 現在の状態と次にやること（引き継ぎ用） |
| [docs/project/timeline.md](docs/project/timeline.md) | 開発の経緯（日ごとに何が起きて何を変えたか） |
| [docs/project/decisions.md](docs/project/decisions.md) | 設計判断の記録（D1〜D22）と未決事項 |
| [docs/project/overview.md](docs/project/overview.md) | プロダクト概要、誰が何に困っているか、設計原則、工程の区分、ユーザー操作 |
| [docs/project/architecture.md](docs/project/architecture.md) | 全体構成、iOS アプリ、サーバー、Managed Agents |
| [docs/project/sound-picture.md](docs/project/sound-picture.md) | 音の絵（スペクトログラム）の設計 |
| [docs/project/demo.md](docs/project/demo.md) | デモ動画の台本と撮る素材 |
| [docs/project/plan.md](docs/project/plan.md) | スケジュール、削る順、デモの筋、受け入れ基準 |
| [docs/project/recording-protocol.md](docs/project/recording-protocol.md) | 検証データの記録手順 |
| [docs/project/constraints.md](docs/project/constraints.md) | イベント上の制約とその解釈 |
| [docs/log/](docs/log/) | 日々の観測と検証の記録 |
