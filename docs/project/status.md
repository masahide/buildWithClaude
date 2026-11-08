# 現在の状態と次にやること

作業を引き継ぐときに最初に読む。終わった項目は消し、結果は [docs/log/](../log/) に、判断は [decisions.md](decisions.md) に書く。1日の区切りに [timeline.md](timeline.md)（開発の経緯）にも1段落足す。

最終更新: 2026-11-08 昼（提出日。デモ動画の作業の前に、SSH のセッションから Mac の画面側のセッションへ引き継ぐ）

## いちばん大事なこと

- **提出期限は今日 2026-11-08 20:00 JST。** 余裕を見て 18 時台に提出する
- 残りの作業は「デモ動画を作る」と「提出する」だけ。機能は足さない。直すのは、デモで見せる場面が動かないときだけ
- 本人はこのあと、Mac の画面の前で Claude Code（デスクトップ版など）を使って作業する。動画の編集も Mac で行う（iMovie など）

## 今日このあとの段取り

| 目安 | 本人 | Claude Code |
| --- | --- | --- |
| 〜13:00 | 休憩。iPhone の画面収録（あれば）を AirDrop で Mac に送る | — |
| 13:00〜16:30 | デモ動画を撮って編集する（3分以内） | [demo.md](demo.md) の台本の言い回しの仕上げ、文字カードの文面、場面ごとの秒数の調整、必要なら追加の画像を描く |
| 16:30〜17:30 | 動画を書き出して見直す | 提出用の「プロジェクト概要」の文を仕上げる（README の冒頭から作る）。README・status・timeline の最終確認 |
| 17:30〜19:00 | 提出（プロジェクト概要、動画の URL、GitHub リポジトリの URL） | 最後のコミットとプッシュ |

提出物（[constraints.md](constraints.md)）: プロジェクト概要、視聴可能な3分デモ動画、公開 GitHub リポジトリ。動画は YouTube の限定公開などで URL を作る。

## デモ動画

- 台本と撮る素材の一覧: [demo.md](demo.md)（8場面、合計 3:00。山場は⑥「コーチが自分から判定の誤りを指摘し、直った」）
- デモ用の画像（`notes/private/demo/`、git 管理外）

  | ファイル | 中身 | 場面 |
  | --- | --- | --- |
  | `1107_v1.png` | 11-07 昼の杯、直す前の判定。「始まり」が空だし（−8 秒）に、「止めた」が静かな渦の途中（27 秒）に立つ | ⑥ |
  | `1107_v2.png` | 同じ杯、コーチの指摘で直した後（0〜57 秒）。v1 と同じ時間軸 | ⑥ |
  | `1108_cup1.png` | 11-08 1杯目（泡が多すぎた）。渦の後半 43 秒あたりに、うっかり空気が入った山 | ④ |
  | `1108_cup2.png` | 11-08 2杯目（良かった）。その山がない | ⑤ |

- 画面に出す文の材料
  - ⑥ コーチの指摘（11-07 昼の杯、`server/data/cups/aedd4308*/status.json` の `diagnosis_v1.judgment_doubt`）: 「止めた線（37.3 秒）が早すぎる可能性がある。スペクトログラムではスチームの音が約 62 秒まで続き、止める間際のキュルキュルに似た下がる音が 61〜63 秒にある。始まりが空だしを拾った可能性もある」
  - ⑤ 予測の当否（11-08 2杯目、`server/data/cups/1d5e24e3*/status.json` の `previous_verdict`）: 「当たり寄り（ただし交絡あり）。追加のジュルジュルを入れない直しは守れていた。膜が薄くなり、自己評価も『泡が多すぎた』から『良かった』に変わった。ただし続けて淹れた杯で、直しの効果とは分けられない」
  - ⑦ 今日のテーマ・あなたの正解・コーチが学んだこと: アプリの「コーチと一緒に育つ」の欄（`GET /coach` と同じ中身）
- 練習なしで撮れる画面: アプリの杯の一覧と診断、「コーチと一緒に育つ」の欄、「コーチに教える」。音の絵は `GET /cups/<id>/sound.png` でも取れる
- 撮影の注意: ピッチャーは洗う前に撮る。名前・住所・機材の型番を映さない（ボイスメモのファイル名に録音場所の住所が入ることがある）

## できていること（2026-11-08 昼）

| 項目 | 状態 |
| --- | --- |
| iOS アプリ | 実機に入れ済み（判定 v2、練習の音を全部送る、二重に送らない）。録音・判定・区切って撮る・送信・診断と音の絵の表示・コーチと一緒に育つ（今日のテーマ、あなたの正解、コーチが学んだこと、教える、閾値の提案の承認） |
| 判定 | v2（D22）。11-05 と 11-07 の録音で本人の耳・音の形と合う。サーバーは音のある杯を今の版で測り直してから診断する |
| サーバー | 自宅の Mac で動いている。**Claude Code のセッションとは切り離して起動してあるので、セッションを閉じても止まらない**。ログは `server/data/logs/server.log` |
| コーチ | 毎杯の診断（Managed Agents＋Outcomes、1〜3 分）、音の絵を見て判定の誤りを `judgment_doubt` に書く、夜の振り返り（記憶を育て、明日のテーマを決める、根拠があれば閾値を提案） |
| 杯の記録 | 実際の杯は 11-04 に2杯、11-07 に2杯（＋送り直しの重複1杯、`duplicate_of` つき）、11-08 に2杯。音のある杯は 11-07 以降の4杯 |
| 夜の振り返り | 11-04・11-07・11-08 に回した。11-08 の結果: 閾値の提案なし。あなたの正解の追加なし（「足さない」は、本人の教え「追加の泡入れはうっかりだった」とずれるので正解にしなかった）。次のテーマ「渦でチリチリやキュッが聞こえたら、ほんの少し上げ、止んだら保つ」 |
| ドキュメント | README は提出用に書き直し済み。decisions は D1〜D22。日々の記録は docs/log/2026-11-03〜08 |

## 環境の注意（この Mac）

- **サーバーを二重に起動しない。** 動いているかは `curl -s localhost:8000/health`。止まっていたら次で起動する（セッションと切り離す形）:
  ```sh
  cd server && set -a && . ~/.config/latte-coach/env && set +a && mkdir -p data/logs && \
    nohup python3 -c 'import os; os.setsid(); os.execvp("uv", ["uv","run","uvicorn","app:app","--host","0.0.0.0","--port","8000"])' \
    > data/logs/server.log 2>&1 < /dev/null & disown
  ```
  止めるときは `pkill -f 'uvicorn app:app'`
- API キーは `~/.config/latte-coach/env`（`ANTHROPIC_API_KEY=...` の1行、git 管理外）。値を表示しない
- サーバーのデータ（杯、音声、記憶の ID、判定の版、振り返りの結果）は `server/data/`（git 管理外）。音声は家の外に出さない（D21）
- 署名: 画面側のセッションなら、キーチェーンの解錠は要らない。SSH 経由だと `errSecInternalComponent` で失敗するので、本人に Claude Code の入力欄から `! security unlock-keychain ~/Library/Keychains/login.keychain-db` を実行してもらう（パスワードは本人が入れる。受け取らない）。11-07 に本人がキーチェーンの自動ロックを外した（戻すときは `security set-keychain-settings -l -u ~/Library/Keychains/login.keychain-db`）
- 無料の Apple ID（Personal Team）。アプリは7日ごとに入れ直しが要る（D12）
- 署名チーム・バンドル ID・サーバー URL は `ios/Config/Local.xcconfig`（git 管理外）。プロジェクトを変えたら `cd ios && xcodegen`
- iPhone への入れ直し（端末の ID は `xcrun devicectl list devices`）:
  ```sh
  cd ios
  xcodebuild -project LatteCoach.xcodeproj -scheme LatteCoach -destination "id=<端末ID>" \
    -derivedDataPath <作業用ディレクトリ> -allowProvisioningUpdates build
  xcrun devicectl device install app --device <端末ID> <作業用ディレクトリ>/Build/Products/Debug-iphoneos/LatteCoach.app
  xcrun devicectl device process launch --terminate-existing --device <端末ID> <バンドル ID>
  ```
- GitHub へのプッシュ: SSH の鍵はこの Mac に無く、本人の接続の鍵の転送で通っている。画面側のセッションでは `git push https://github.com/masahide/buildWithClaude.git main` で、保存済みの認証を使ってプッシュできる（11-08 に確かめた）
- 11-08 昼に、参加者限定の資料の要約（docs/hackathon/）を履歴から消して強制プッシュした。元の履歴の控えは `notes/private/backup/`
- 夜の振り返りを手で回す: `curl -X POST "localhost:8000/review?day=YYYY-MM-DD"`（結果は `server/data/reviews/`、約 30 分）

## 提出後にやること（README の「次にやること」と同じ）

- **ElevenLabs の Starter プラン（11-08 契約、最初の月 1 ドル、翌月から月 6 ドル）を解約する。** キーは `~/.config/latte-coach/env` の `ELEVENLABS_API_KEY`

- 他の人・他のマシン（特に短いスチーム）の録音で判定を確かめる
- 撹拌中のチリチリを数える（4〜8 kHz の帯域は送っている）
- 音の絵の描き方をコーチ自身が変えられるようにする
- アプリで自分の音の絵を見られるようにする
- 製品名を決める（アプリは「スチームコーチ」、README は「ラテアートAIコーチ」のまま）
