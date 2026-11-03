# ラテアートAIコーチ

家庭でラテアートを練習する人のための、ミルクスチームに特化した、練習に溶け込むコーチ。「開始」を押してスマホを置いておくだけで、スチームの音とピッチャーの残りの写真1枚から、1杯ごとに「原因の工程」「次の1杯で直す点ひとつ」「次の杯で起きるはずの変化」が届く。次の杯でその予測が当たったかを確かめ、当たった直し方が「あなたの正解」として溜まる。翌朝には、前日の杯をまたいだ癖と今日のテーマが届く。

ラテアートの出来はミルクのスチームで決まるのに、スチームの正解は熟練者の耳の中にしかない。完成した模様を採点するアプリはあるが、失敗の原因はスチームにあり、写真には写らず音にしか残らない。家で一人で練習すると、失敗しても原因がエア入れか撹拌か分からず、同じ失敗を繰り返す。このコーチは、音で工程を聴き分け、次の1杯で仮説を検証する（[docs/project/decisions.md D10](docs/project/decisions.md#d10-対象をミルクスチームに特化し工程をエア入れ撹拌の2つにする)）。渦の回転方向のように音で分からないものは、動作ではなく結果で確かめる（[D9](docs/project/decisions.md#d9-音で分からないものを明文化する)）。

[Built with Claude: Japan 2026](https://cerebralvalley.ai/events/~/e/built-with-claude-japan2026) への応募作品（テーマ1「あなたにしかない深さを。」）。

> 開発中。セットアップと再現手順、開発過程での Claude Code の使い方、次にやることは実装に合わせて追記する。

## 構成

iOS ネイティブアプリ＋薄いサーバー＋Claude Managed Agents。生の音声は端末から出さず、端末で計算した音響特徴量（スカラー値と相対値の包絡）とピッチャーの残りの写真だけを送る。詳細は [docs/project/architecture.md](docs/project/architecture.md)。

## ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [docs/project/overview.md](docs/project/overview.md) | プロダクト概要、誰が何に困っているか、設計原則、工程の区分、ユーザー操作 |
| [docs/project/architecture.md](docs/project/architecture.md) | 全体構成、iOS アプリ、サーバー、Managed Agents |
| [docs/project/decisions.md](docs/project/decisions.md) | 設計判断の記録と未決事項 |
| [docs/project/plan.md](docs/project/plan.md) | スケジュール、削る順、デモの筋、受け入れ基準 |
| [docs/project/recording-protocol.md](docs/project/recording-protocol.md) | 検証データの記録手順 |
| [docs/project/constraints.md](docs/project/constraints.md) | イベント上の制約とその解釈 |
| [docs/log/](docs/log/) | 日々の観測と検証の記録 |
| [docs/hackathon/participant-guide.md](docs/hackathon/participant-guide.md) | ハッカソン参加者ガイドの要約 |
| [docs/hackathon/kickoff.md](docs/hackathon/kickoff.md) | キックオフの要約 |
