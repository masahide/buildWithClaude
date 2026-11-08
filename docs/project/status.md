# 現在の状態と次にやること

作業を引き継ぐときに最初に読む。終わった項目は消し、結果は [docs/log/](../log/) に、判断は [decisions.md](decisions.md) に書く。1日の区切りに [timeline.md](timeline.md)（開発の経緯）にも1段落足す。

最終更新: 2026-11-08 夕方（デモ動画を作り、YouTube に限定公開した。あとは本人がフォームから提出する）

## いちばん大事なこと

- **提出期限は今日 2026-11-08 20:00 JST。** 18 時台に提出する
- 残りは提出だけ。機能もドキュメントも足さない
- 提出フォームの下書きは `notes/private/submission.md`（git 管理外）。概要は冒頭の1文を含めて500字以内に収めてある

## 提出物

| 提出物 | 状態 |
| --- | --- |
| 公開 GitHub リポジトリ | https://github.com/masahide/buildWithClaude （公開、MIT ライセンス。参加者限定の資料の要約は履歴から消した） |
| デモ動画 | https://youtu.be/DSAeuG_FyZk （限定公開、2:59）。台本は [demo.md](demo.md)、動画のコードは [demo-video/](../../demo-video/)（Remotion）、語りは ElevenLabs の声（[scripts/demo/narration.py](../../scripts/demo/narration.py)） |
| プロジェクト概要とフォームの回答 | 下書き済み（`notes/private/submission.md`） |

## デモ動画の作り直し方

- 素材は `notes/private/demo/`、動画用にまとめたものは `demo-video/public/`（どちらも git 管理外）
- `cd demo-video && npx remotion render src/index.ts Demo out/demo.mp4`（約3分）。台本の秒数は `src/Demo.tsx` の `SCENES`
- 語りを作り直す: `set -a; . ~/.config/latte-coach/env; set +a; uv run --with requests python scripts/demo/narration.py notes/private/demo/voice/v3 <場面>`。読み間違える言葉は仮名に開く

## できていること（2026-11-08 昼）

| 項目 | 状態 |
| --- | --- |
| iOS アプリ | 実機に入れ済み（判定 v2、練習の音を全部送る、二重に送らない）。録音・判定・区切って撮る・送信・診断と音の絵の表示・コーチと一緒に育つ（今日のテーマ、あなたの正解、コーチが学んだこと、教える、閾値の提案の承認） |
| 判定 | v2（D22）。11-05 と 11-07 の録音で本人の耳・音の形と合う。サーバーは音のある杯を今の版で測り直してから診断する |
| サーバー | 自宅の Mac で動いている。**Claude Code のセッションとは切り離して起動してあるので、セッションを閉じても止まらない**。ログは `server/data/logs/server.log` |
| コーチ | 毎杯の診断（Managed Agents＋Outcomes、1〜3 分）、音の絵を見て判定の誤りを `judgment_doubt` に書く、夜の振り返り（記憶を育て、明日のテーマを決める、根拠があれば閾値を提案） |
| 杯の記録 | 実際の杯は 11-04 に2杯、11-07 に2杯（＋送り直しの重複1杯、`duplicate_of` つき）、11-08 に2杯。音のある杯は 11-07 以降の4杯 |
| 夜の振り返り | 11-04・11-07・11-08 に回した。11-08 の結果: 閾値の提案なし。あなたの正解の追加なし（「足さない」は、本人の教え「追加の泡入れはうっかりだった」とずれるので正解にしなかった）。次のテーマ「渦でチリチリやキュッが聞こえたら、ほんの少し上げ、止んだら保つ」 |
| ドキュメント | README は提出用に書き直し済み。decisions は D1〜D23。日々の記録は docs/log/2026-11-03〜08 |

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
