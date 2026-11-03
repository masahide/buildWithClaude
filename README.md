# ラテアートAIコーチ

家庭でラテアートを練習する人のための、練習に溶け込むコーチ。「開始」を押してスマホを置いておくだけで、スチームの音と完成写真1枚から、1杯ごとに「原因の工程」と「次の1杯で直す点ひとつ」が届く。翌朝には、前日の杯をまたいだ癖と今日のテーマが届く。

[Built with Claude: Japan 2026](https://cerebralvalley.ai/events/~/e/built-with-claude-japan2026) への応募作品（テーマ1「あなたにしかない深さを。」）。

> 開発中。セットアップと再現手順は実装に合わせて追記する。

## 構成

iOS ネイティブアプリ＋薄いサーバー＋Claude Managed Agents。生の音声は端末から出さず、端末で計算した音響特徴量と完成写真だけを送る。詳細は [docs/project/architecture.md](docs/project/architecture.md)。

## ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [docs/project/overview.md](docs/project/overview.md) | プロダクト概要、設計原則、ユーザー操作 |
| [docs/project/architecture.md](docs/project/architecture.md) | 全体構成、iOS アプリ、サーバー、Managed Agents |
| [docs/project/decisions.md](docs/project/decisions.md) | 設計判断の記録と未決事項 |
| [docs/project/plan.md](docs/project/plan.md) | スケジュール、デモの筋、受け入れ基準 |
| [docs/project/recording-protocol.md](docs/project/recording-protocol.md) | 検証データの記録手順 |
| [docs/project/constraints.md](docs/project/constraints.md) | イベント上の制約とその解釈 |
| [docs/log/](docs/log/) | 日々の観測と検証の記録 |
| [docs/hackathon/participant-guide.md](docs/hackathon/participant-guide.md) | ハッカソン参加者ガイドの要約 |
| [docs/hackathon/kickoff.md](docs/hackathon/kickoff.md) | キックオフの要約 |
