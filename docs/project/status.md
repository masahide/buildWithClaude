# 現在の状態と次にやること

作業を引き継ぐときに最初に読む。終わった項目は消し、結果は [docs/log/](../log/) に、判断は [decisions.md](decisions.md) に書く。

最終更新: 2026-11-03 夜

## 目標

**11-05 の夜までに「録る → 送る → 診断がアプリに表示される」の一周を、手動区切りで回す**（[decisions.md D11](decisions.md#d11-最初の一周は手動区切りで回し自動区切りと包絡を後回しにする)）。残りの日はデモ素材の撮影と検証データに充てる。

## できていること（2026-11-03）

| 項目 | 状態 |
| --- | --- |
| iOS アプリ（`ios/`） | 実機（iPhone 15 Pro Max）で起動。録音、背景音の測定、特徴量、「この杯を区切って撮る」、スチーム終了の通知、写真、送信、結果の表示、送り直し |
| 特徴量のテスト | シミュレーターで5本通過（合成音）。実際のスチーム音ではまだ試していない |
| サーバー（`server/`） | FastAPI。`COACH_BACKEND=fake` で、iPhone から Wi-Fi で送った杯に2秒で固定の診断が返り、アプリに表示されることを確認した |
| 本物の診断（`messages` / `managed`） | コードはあるが、**API キーが未設定のため一度も回していない** |
| 診断の待ち時間の計測 | スクリプト（`scripts/latency/measure.py`）はあるが未実行 |
| Dreaming | 申請済み・承認待ち。計画は承認がない前提で進める |

## 次にやること（順番どおり）

1. **API キーを用意する（本人の作業）**
   - キーは `~/.config/latte-coach/env` に `ANTHROPIC_API_KEY=...` の1行で置く（`chmod 600`）。リポジトリにも会話にも出さない
   - 本人にキーをクリップボードにコピーしてもらい、Claude Code のプロンプトから次を実行してもらう:
     `! mkdir -p ~/.config/latte-coach && (printf 'ANTHROPIC_API_KEY='; pbpaste) > ~/.config/latte-coach/env && chmod 600 ~/.config/latte-coach/env && echo saved`
   - 使うときは `set -a; . ~/.config/latte-coach/env; set +a` で読み込む。キーの値を表示しない
2. **診断の待ち時間を測る**
   - 本人に今日撮ったピッチャーの写真を Mac に置いてもらう（AirDrop なら `~/Downloads`）。HEIC なら `sips -s format jpeg IN.HEIC --out OUT.jpg` で変換する
   - `uv run scripts/latency/measure.py OUT.jpg --mode managed --mode messages`
   - 結果は `scripts/latency/results/`（git 管理外）。要点を `docs/log/` に書く
3. **方式を決める**: [decisions.md の未決](decisions.md#未決)の1行目を閉じる。数十秒〜1分なら Managed Agents、数分なら Messages API。Dreaming はセッションの記録しか読まないので、Messages API にした場合は振り返りだけ Managed Agents で回す（[log/2026-11-03.md](../log/2026-11-03.md#dreaming-の申請)）
4. **サーバーを本物の診断に切り替える**: 決めた方式の `COACH_BACKEND` で起動し直し、アプリの「送り直す」で、既にある杯に本物の診断が付くか確かめる
5. **翌朝（11-04）の実録音**: 本人がカウンターに置いて1〜2杯。スチーム終了の通知が来るか、特徴量（スチームの秒数・エア入れの割合・破裂音の回数）がもっともらしいかを見て、`ios/LatteCoach/Audio/FeatureExtractor.swift` の `FeatureThresholds` を調整する
6. 続き: `/profile.md` の内容を本人から聞く（マシン、ノズルの穴数、ピッチャー容量、ミルクの銘柄と量、目指す泡）→ メモリストア → 夜の振り返り（[plan.md](plan.md#スケジュール) のフェーズ2〜3）

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
- サーバーの起動: `cd server && COACH_BACKEND=fake uv run uvicorn app:app --host 0.0.0.0 --port 8000`。iPhone と Mac は同じ Wi-Fi に置く。Mac がスリープすると届かない
- iOS の初回送信は、ローカルネットワークの許可が出るまで「Could not connect to the server.」で失敗する。設定 → プライバシーとセキュリティ → ローカルネットワークで許可する
- アプリの記録は iPhone から読み出せる: `xcrun devicectl device copy from --device <端末ID> --domain-type appDataContainer --domain-identifier <バンドル ID> --source Documents/Cups/cups.json --destination <保存先>`
- 外部から取ってきたバイナリの実行は、権限の自動判定で止められる。Xcode は App Store から入れた
