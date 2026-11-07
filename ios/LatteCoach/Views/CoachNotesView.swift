import SwiftUI

/// コーチと一緒に育つ: 今日のテーマ、あなたの正解、コーチが学んだこと（夜の振り返りが書く。decisions.md D18）
@MainActor
final class CoachNotesModel: ObservableObject {
    @Published private(set) var notes: CoachClient.Notes?
    @Published private(set) var error: String?

    func teach(_ text: String) async -> Bool {
        guard let client = CoachClient.fromBundle() else { return false }
        do {
            try await client.teach(text)
            await refresh()
            return true
        } catch {
            self.error = error.localizedDescription
            return false
        }
    }

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
    @State private var lesson = ""
    @State private var sending = false

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
                VStack(alignment: .leading, spacing: 6) {
                    Text("コーチに教える").font(.caption).foregroundStyle(.secondary)
                    TextField("例: 27〜32秒は追加の泡入れだった", text: $lesson, axis: .vertical)
                        .lineLimit(1...4)
                    Button(sending ? "送信中…" : "教える") {
                        let text = lesson
                        sending = true
                        Task {
                            if await model.teach(text) { lesson = "" }
                            sending = false
                        }
                    }
                    .disabled(lesson.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || sending)
                }
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
