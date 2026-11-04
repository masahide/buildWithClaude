# 現在の状態と次にやること

作業を引き継ぐときに最初に読む。終わった項目は消し、結果は [docs/log/](../log/) に、判断は [decisions.md](decisions.md) に書く。

最終更新: 2026-11-04 朝（実録音の最初の2杯）

## 目標

**11-05 の夜までに「録る → 送る → 診断がアプリに表示される」の一周を、手動区切りで回す**（[decisions.md D11](decisions.md#d11-最初の一周は手動区切りで回し自動区切りと包絡を後回しにする)）。残りの日はデモ素材の撮影と検証データに充てる。

## できていること（2026-11-03）

| 項目 | 状態 |
| --- | --- |
| iOS アプリ（`ios/`） | 実機（iPhone 15 Pro Max）で起動。録音、背景音の測定、特徴量、「この杯を区切って撮る」、スチーム終了の通知、写真、送信、結果の表示、送り直し |
| 特徴量のテスト | シミュレーターで5本通過（合成音）。実際のスチーム音ではまだ試していない |
| サーバー（`server/`） | FastAPI。iPhone から Wi-Fi で送った杯に、Managed Agents＋Outcomes の本物の診断が返り、アプリに表示される（ダミーの杯2杯で確認） |
| 診断の方式 | Managed Agents＋Outcomes に決めた（D13）。送ってから約1〜2分（68 / 101 / 190 秒）。Messages API は約15秒で、`COACH_BACKEND=messages` で戻せる |
| API キー | `~/.config/latte-coach/env` にある（`ANTHROPIC_API_KEY=...` の1行、git 管理外）。使うときは `set -a; . ~/.config/latte-coach/env; set +a` で読み込む。値を表示しない |
| Dreaming | 申請済み・承認待ち。計画は承認がない前提で進める |

## 次にやること（順番どおり）

1. **包絡で相の判定を作り直す**: 11-04 の最初の2杯で、40〜60 秒のスチームが 14〜19 秒しか検出されなかった（[log/2026-11-04.md](../log/2026-11-04.md)）。閾値をゆるめ、包絡（0.1 秒ごとの3帯域、背景音比）をサーバーに送るようにした（D14）。届いた杯の `server/data/cups/*/meta.json` の `envelope` を見て、空だし・始めと終わりの「キュルルル」・泡入れの「ジュルジュル」・渦の位置を確かめ、`FeatureExtractor.swift` のスチーム区間とエア入れ／撹拌の判定を作り直す
2. **実際の杯の診断を見る**: 実録音の杯で、診断の中身（原因1つ・耳と手と時間で実行できる直す点1つ・予測1つ）と `elapsed_sec` を確かめ、`docs/log/` に書く。直す点が数段の手順になりがちなので、気になればルーブリックで絞る
3. 続き: `/profile.md` の内容を本人から聞く（マシン、ノズルの穴数、ピッチャー容量、ミルクの銘柄と量、目指す泡）→ メモリストア → 夜の振り返り（[plan.md](plan.md#スケジュール) のフェーズ2〜3）

気づいている点（直す順は上の作業の後でよい）:

- サーバーの `_previous_cup` は「診断が済んだ最新の杯」を前の杯にする。診断中（1〜2分）に次の杯を送ると、その杯はひとつ前の杯と比較される。日をまたいだ杯とも比較するので、夜の振り返りを作るときに「同じ練習回」の境界（練習の開始〜終了、または一定時間の空き）を決める
- 製品名: アプリの表示名は「スチームコーチ」、サーバーは "Steam Coach"。README と CLAUDE.md の「ラテアートAIコーチ」とどちらかに揃える（[decisions.md 未決](decisions.md#未決)、期限 11-07）
- `COACH_BACKEND` の既定値は coach.py と README で `messages` のまま。D13 で `managed` に決めたので、既定値を合わせる

## 環境の注意（この Mac）

- 開発は Mac だけで行う。Windows では編集しない（D11）
- **署名には Mac のログインキーチェーンの解錠が要る。** SSH 経由のシェルからだと `errSecInternalComponent` で署名に失敗する。本人に `! security unlock-keychain ~/Library/Keychains/login.keychain-db` を実行してもらう（パスワードは本人が入れる。受け取らない）。再起動するとまたロックされる
- 無料の Apple ID（Personal Team）で署名している。アプリは7日ごとに入れ直しが要る（D12）
- 署名チーム・バンドル ID・サーバー URL は `ios/Config/Local.xcconfig`（git 管理外、この Mac にだけある）。プロジェクトを変えたら `cd ios && xcodegen` で作り直す
- iPhone への入れ直し（端末の ID は `xcrun devicectl list devices` で確かめる）:
  ```sh
  cd ios
  xcodebuild -project LatteCoach.xcodeproj -scheme LatteCoach -destination "id=<端末ID>" \
    -derivedDataPath <作業用ディレクトリ> -allowProvisioningUpdates build
  xcrun devicectl device install app --device <端末ID> <作業用ディレクトリ>/Build/Products/Debug-iphoneos/LatteCoach.app
  xcrun devicectl device process launch --terminate-existing --device <端末ID> <バンドル ID>
  ```
  iPhone がロック中だと起動だけ失敗する。本人に解除してもらう
- サーバーの起動: `cd server && set -a && . ~/.config/latte-coach/env && set +a && COACH_BACKEND=managed uv run uvicorn app:app --host 0.0.0.0 --port 8000`。API を呼ばずに通しを確かめるときは `COACH_BACKEND=fake`。Managed Agents のエージェントと環境の ID は `server/data/managed_ids.json`（git 管理外）に保存され、使い回される。iPhone と Mac は同じ Wi-Fi に置く。Mac がスリープすると届かない
- iOS の初回送信は、ローカルネットワークの許可が出るまで「Could not connect to the server.」で失敗する。設定 → プライバシーとセキュリティ → ローカルネットワークで許可する
- アプリの記録は iPhone から読み出せる: `xcrun devicectl device copy from --device <端末ID> --domain-type appDataContainer --domain-identifier <バンドル ID> --source Documents/Cups/cups.json --destination <保存先>`
- 外部から取ってきたバイナリの実行は、権限の自動判定で止められる。Xcode は App Store から入れた
