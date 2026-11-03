# CLAUDE.md

ラテアートAIコーチ（Built with Claude: Japan 2026 応募作品）のリポジトリ。プロダクトの全体像は [README.md](README.md) と [docs/project/](docs/project/) を読むこと。

**作業を始める前に [docs/project/status.md](docs/project/status.md)（現在の状態と次にやること）を読むこと。** 区切りがついたら更新する。

## 必ず守ること

- **提出期限は 2026-11-08 20:00 JST。** 優先度はこの期限から逆算する（[docs/project/plan.md](docs/project/plan.md)）
- **コードはすべてこのリポジトリで新規に書く。** 本人が過去に作った iOS アプリのコードや、イベント前に作った変数表を持ち込まない（[docs/project/constraints.md](docs/project/constraints.md)）
- **公開リポジトリである。** API キーなどの秘密情報はコミットしない。環境変数で扱う
- `notes/private/` は git 管理外の非公開メモ。内容を公開ドキュメントやコミットに転記しない
- 生の音声を端末外に送る実装にしない。送るのは音響特徴量（スカラー値と相対値の包絡）とピッチャーの残りの写真だけ
- 製品の主語はミルクスチーム。注ぎやカップの模様は診断・採点しない（[docs/project/decisions.md D10](docs/project/decisions.md)）
- コーチの返答は「原因の工程1つ（エア入れ／撹拌）」「次の1杯で直す点1つ」「次の杯で起きるはずの変化1つ」に絞る。直す点は耳・手・時間で実行できる言葉にする

## ドキュメントの更新

- 設計を変えたら [docs/project/decisions.md](docs/project/decisions.md) に日付と理由を追記する
- 検証や観測の結果は `docs/log/YYYY-MM-DD.md` に書く
- ドキュメントは日本語で書く
