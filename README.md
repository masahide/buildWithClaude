# ラテアートAIコーチ

家庭でラテアートを練習する人のための、ミルクスチームに特化した、練習に溶け込むコーチ。「開始」を押してスマホを置いておくだけで、スチームの音とピッチャーの残りの写真1枚から、1杯ごとに「原因の工程」「次の1杯で直す点ひとつ」「次の杯で起きるはずの変化」が届く。次の杯でその予測が当たったかを確かめ、当たった直し方が「あなたの正解」として溜まる。翌朝には、前日の杯をまたいだ癖と今日のテーマが届く。

ラテアートの出来はミルクのスチームで決まるのに、スチームの正解は熟練者の耳の中にしかない。完成した模様を採点するアプリはあるが、失敗の原因はスチームにあり、写真には写らず音にしか残らない。家で一人で練習すると、失敗しても原因がエア入れか撹拌か分からず、同じ失敗を繰り返す。このコーチは、音で工程を聴き分け、次の1杯で仮説を検証する（[docs/project/decisions.md D10](docs/project/decisions.md#d10-対象をミルクスチームに特化し工程をエア入れ撹拌の2つにする)）。渦の回転方向のように音で分からないものは、動作ではなく結果で確かめる（[D9](docs/project/decisions.md#d9-音で分からないものを明文化する)）。

[Built with Claude: Japan 2026](https://cerebralvalley.ai/events/~/e/built-with-claude-japan2026) への応募作品（テーマ1「あなたにしかない深さを。」）。

> 開発中。セットアップと再現手順、開発過程での Claude Code の使い方、次にやることは実装に合わせて追記する。

## 構成

iOS ネイティブアプリ＋薄いサーバー＋Claude Managed Agents。生の音声は家の外に出さない。iPhone は練習の音を全部、自宅の Mac のサーバーに送り、サーバーで何度でもスチームを切り出し直し、測り直し、絵を描き直せるようにする。Claude には音そのものではなく、音から作った数値とスペクトログラムの画像、ピッチャーの残りの写真を渡す（[decisions.md D21](docs/project/decisions.md)）。詳細は [docs/project/architecture.md](docs/project/architecture.md)。

## セットアップ

必要なもの: Mac（Xcode 27 以降）、iPhone、[uv](https://docs.astral.sh/uv/)、[XcodeGen](https://github.com/yonaskolb/XcodeGen)、Anthropic の API キー。有償の Apple Developer Program は不要（[decisions.md D12](docs/project/decisions.md#d12-無料の-apple-id-で開発しリモートのプッシュ通知を使わない)）。

### サーバー

```sh
cd server
export ANTHROPIC_API_KEY=...        # コミットしない
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

`COACH_BACKEND` で診断の方式を選ぶ。`managed`（既定）は Managed Agents のセッションに Outcomes を付けて回す。`messages` は Messages API を1回呼ぶ（速いが採点役がない）。`fake` は API を呼ばずに固定の診断を返すので、アプリとの通しの確認に使う。杯の記録は `server/data/`（git 管理外）に残る。

### iOS アプリ

```sh
cd ios
cp Config/Local.xcconfig.example Config/Local.xcconfig   # Team ID・バンドル ID・サーバー URL を書く
xcodegen
open LatteCoach.xcodeproj
```

サーバーの URL は、同じ Wi-Fi にある Mac を `http:/$()/<Mac の名前>.local:8000` の形で書く（xcconfig では `//` がコメントになるため）。

### 診断の待ち時間の計測

```sh
uv run scripts/latency/measure.py ピッチャーの写真.jpg --mode managed --mode messages
```

## ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [docs/project/status.md](docs/project/status.md) | 現在の状態と次にやること（引き継ぎ用） |
| [docs/project/timeline.md](docs/project/timeline.md) | 開発の経緯（日ごとに何が起きて何を変えたか） |
| [docs/project/overview.md](docs/project/overview.md) | プロダクト概要、誰が何に困っているか、設計原則、工程の区分、ユーザー操作 |
| [docs/project/architecture.md](docs/project/architecture.md) | 全体構成、iOS アプリ、サーバー、Managed Agents |
| [docs/project/decisions.md](docs/project/decisions.md) | 設計判断の記録と未決事項 |
| [docs/project/plan.md](docs/project/plan.md) | スケジュール、削る順、デモの筋、受け入れ基準 |
| [docs/project/recording-protocol.md](docs/project/recording-protocol.md) | 検証データの記録手順 |
| [docs/project/constraints.md](docs/project/constraints.md) | イベント上の制約とその解釈 |
| [docs/log/](docs/log/) | 日々の観測と検証の記録 |
| [docs/hackathon/participant-guide.md](docs/hackathon/participant-guide.md) | ハッカソン参加者ガイドの要約 |
| [docs/hackathon/kickoff.md](docs/hackathon/kickoff.md) | キックオフの要約 |
