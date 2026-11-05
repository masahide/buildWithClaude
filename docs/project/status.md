# 現在の状態と次にやること

作業を引き継ぐときに最初に読む。終わった項目は消し、結果は [docs/log/](../log/) に、判断は [decisions.md](decisions.md) に書く。1日の区切りに [timeline.md](timeline.md)（開発の経緯）にも1段落足す。

最終更新: 2026-11-05 朝（ボイスメモで判定を作り直した）

## 目標

**11-05 の夜までに「録る → 送る → 診断がアプリに表示される」の一周を、手動区切りで回す**（[decisions.md D11](decisions.md#d11-最初の一周は手動区切りで回し自動区切りと包絡を後回しにする)）。残りの日はデモ素材の撮影と検証データに充てる。

## できていること（2026-11-04 時点）

| 項目 | 状態 |
| --- | --- |
| iOS アプリ（`ios/`） | 実機（iPhone 15 Pro Max）で起動。録音、背景音の測定、特徴量、「この杯を区切って撮る」、スチーム終了の通知、写真、送信、結果の表示、送り直し。11-04 の版で、検出をゆるめ、包絡を送り、起動時に止まった杯を立て直す（実機に入れ済み） |
| 特徴量 | 11-05 にボイスメモ1本で判定を作り直した（D15）。その録音では、スチーム 56 秒、始めのキュルルル 4.6 秒、泡入れ 29%。合成音のテスト5本も実際の並びに合わせて作り直し、通過。**iPhone にはまだ入れていない**（11-04 の版のまま） |
| サーバー（`server/`） | FastAPI。iPhone から Wi-Fi で送った杯に、Managed Agents＋Outcomes の本物の診断が返り、アプリに表示される。実際のスチームの2杯で一周した。昨夜のダミーの杯は `server/data/dummy/` に移してあり、前の杯の比較には使われない |
| 予測の検証（D7） | 実際の杯で初めて回った。2杯目が1杯目の予測（ゴボゴボが減る）を「当たり」と判定し、他の条件も変わったので直し方だけの効果とは言い切れない、と断った |
| 診断の方式 | Managed Agents＋Outcomes に決めた（D13）。送ってから約1〜2分（計測 68 秒、ダミー 101 / 190 秒、実際の杯 104 / 127 秒）。2分を少し超える杯があるので、もう数杯見て判断する。Messages API は約15秒で、`COACH_BACKEND=messages` で戻せる |
| API キー | `~/.config/latte-coach/env` にある（`ANTHROPIC_API_KEY=...` の1行、git 管理外）。使うときは `set -a; . ~/.config/latte-coach/env; set +a` で読み込む。値を表示しない |
| Dreaming | 申請済み・承認待ち。計画は承認がない前提で進める |

## 次にやること（順番どおり）

1. **判定の作り直しを確かめて iPhone に入れる**: 11-05 にボイスメモ1本で、スチーム区間と相の判定を作り直した（[log/2026-11-05.md](../log/2026-11-05.md)、D15）。本人の2本目のボイスメモ（`~/Downloads` に AirDrop で届く）を `notes/private/recordings/` に中立な名前でコピーし（元のファイル名に録音場所の住所が入ることがある）、`afconvert -f WAVE -d LEF32@48000 -c 1` で変換する。アプリと同じ判定を Mac で当てて、境が耳で聞いた位置から数秒以内か確かめる。合えば iPhone に入れ直す（キーチェーンの解錠が必要）
2. **実際の杯の診断を見る**: 実録音の杯で、診断の中身（原因1つ・耳と手と時間で実行できる直す点1つ・予測1つ）と `elapsed_sec` を確かめ、`docs/log/` に書く。直す点が数段の手順になりがちなので、気になればルーブリックで絞る
3. 続き: `/profile.md` の内容を本人から聞く（マシン、ノズルの穴数、ピッチャー容量、ミルクの銘柄と量、目指す泡）→ メモリストア → 夜の振り返り（[plan.md](plan.md#スケジュール) のフェーズ2〜3）

気づいている点（直す順は上の作業の後でよい）:

- サーバーの `_previous_cup` は「診断が済んだ最新の杯」を前の杯にする。診断中（1〜2分）に次の杯を送ると、その杯はひとつ前の杯と比較される。日をまたいだ杯とも比較するので、夜の振り返りを作るときに「同じ練習回」の境界（練習の開始〜終了、または一定時間の空き）を決める
- 製品名: アプリの表示名は「スチームコーチ」、サーバーは "Steam Coach"。README と CLAUDE.md の「ラテアートAIコーチ」とどちらかに揃える（[decisions.md 未決](decisions.md#未決)、期限 11-07）

## 環境の注意（この Mac）

- 開発は Mac だけで行う。Windows では編集しない（D11）
- **署名には Mac のログインキーチェーンの解錠が要る。** SSH 経由のシェルからだと `errSecInternalComponent` で署名に失敗する。本人に **Claude Code の入力欄から** `! security unlock-keychain ~/Library/Keychains/login.keychain-db` を実行してもらう（パスワードは本人が入れる。受け取らない）。Mac の「ターミナル」アプリやキーチェーンアクセスで解錠しても、SSH 側のセッションには効かない。解錠できたかは `security show-keychain-info ~/Library/Keychains/login.keychain-db` で確かめる（`no-timeout` と出れば解錠済み）。再起動するとまたロックされる
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
- **サーバーは Claude Code のセッションを閉じると止まる。** 11-04 の朝は止まっていて、アプリの送信が時間切れになった。練習の前に起動しているか確かめる（`curl -s localhost:8000/health`）
- サーバーの起動: `cd server && set -a && . ~/.config/latte-coach/env && set +a && COACH_BACKEND=managed uv run uvicorn app:app --host 0.0.0.0 --port 8000`。API を呼ばずに通しを確かめるときは `COACH_BACKEND=fake`。Managed Agents のエージェントと環境の ID は `server/data/managed_ids.json`（git 管理外）に保存され、使い回される。iPhone と Mac は同じ Wi-Fi に置く。Mac がスリープすると届かない
- iOS の初回送信は、ローカルネットワークの許可が出るまで「Could not connect to the server.」で失敗する。設定 → プライバシーとセキュリティ → ローカルネットワークで許可する
- アプリの記録は iPhone から読み出せる: `xcrun devicectl device copy from --device <端末ID> --domain-type appDataContainer --domain-identifier <バンドル ID> --source Documents/Cups/cups.json --destination <保存先>`
- 外部から取ってきたバイナリの実行は、権限の自動判定で止められる。Xcode は App Store から入れた
