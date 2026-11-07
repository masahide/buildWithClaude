import SwiftUI

/// コーチと一緒に育つ: 今日のテーマ、あなたの正解、コーチが学んだこと（夜の振り返りが書く。decisions.md D18）
@MainActor
final class CoachNotesModel: ObservableObject {
    @Published private(set) var notes: CoachClient.Notes?
    @Published private(set) var error: String?

    func refresh() async {
        guard let client = CoachClient.fromBundle() else { return }
        do {
            notes = try await client.notes()
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }
}

struct CoachNotesSection: View {
    @ObservedObject var model: CoachNotesModel

    var body: some View {
        Section("コーチと一緒に育つ") {
            if let n = model.notes {
                VStack(alignment: .leading, spacing: 4) {
                    Text("今日のテーマ").font(.caption).foregroundStyle(.secondary)
                    Text(Self.body(n.today)).font(.headline)
                }
                DisclosureGroup("あなたの正解") { Text(Self.body(n.rules)).font(.callout) }
                DisclosureGroup("コーチが学んだこと") { Text(Self.body(n.reading)).font(.callout) }
                DisclosureGroup("杯をまたいだ癖") { Text(Self.body(n.tendencies)).font(.callout) }
            } else if let e = model.error {
                Text(e).font(.caption).foregroundStyle(.red)
            } else {
                Text("読み込み中…").foregroundStyle(.secondary)
            }
        }
    }

    /// 先頭の見出し（# ...）を落とし、残りをマークダウンとして表示する
    static func body(_ md: String) -> AttributedString {
        let lines = md.split(separator: "\n", omittingEmptySubsequences: false)
            .drop { $0.hasPrefix("# ") || $0.trimmingCharacters(in: .whitespaces).isEmpty }
        let text = lines.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)
        let opts = AttributedString.MarkdownParsingOptions(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        return (try? AttributedString(markdown: text.isEmpty ? "（まだない）" : text, options: opts))
            ?? AttributedString(text)
    }
}
