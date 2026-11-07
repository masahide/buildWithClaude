import SwiftUI

/// コーチと一緒に育つ: 今日のテーマ、あなたの正解、コーチが学んだこと（夜の振り返りが書く。decisions.md D18）
@MainActor
final class CoachNotesModel: ObservableObject {
    @Published private(set) var notes: CoachClient.Notes?
    @Published private(set) var error: String?
    @Published private(set) var proposal: CoachClient.Proposal?
    @Published private(set) var means: [String: String] = [:]
    @Published private(set) var paramsVersion: Int?

    func decide(accept: Bool) async {
        guard let client = CoachClient.fromBundle() else { return }
        do {
            try await client.decide(accept: accept)
            await refresh()
        } catch {
            self.error = error.localizedDescription
        }
    }

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
            let p = try await client.proposal()
            proposal = p.proposal
            means = p.means
            paramsVersion = p.current_version
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
            if let p = model.proposal {
                ProposalView(proposal: p, means: model.means) { accept in
                    Task { await model.decide(accept: accept) }
                }
            }
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
                if let v = model.paramsVersion {
                    Text("判定の版: v\(v)（次に練習を開始したときから使う）").font(.caption2).foregroundStyle(.secondary)
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

/// コーチの判定の調整の提案。本人が適用するか見送るかを決める（decisions.md D20）
struct ProposalView: View {
    let proposal: CoachClient.Proposal
    let means: [String: String]
    var decide: (Bool) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("コーチから判定の調整の提案", systemImage: "slider.horizontal.3").font(.headline)
            Text(proposal.reason)
            ForEach(proposal.changes.keys.sorted(), id: \.self) { k in
                VStack(alignment: .leading, spacing: 2) {
                    Text("\(k): \(Self.fmt(proposal.before[k])) → \(Self.fmt(proposal.changes[k]))").font(.callout.monospaced())
                    if let m = means[k] { Text(m).font(.caption2).foregroundStyle(.secondary) }
                }
            }
            DisclosureGroup("根拠") { Text(proposal.evidence).font(.caption) }
            Text("適用すると判定の版が上がり、前の杯と数値を直接比べられなくなります。").font(.caption2).foregroundStyle(.secondary)
            HStack {
                Button("適用する") { decide(true) }.buttonStyle(.borderedProminent)
                Button("見送る") { decide(false) }.buttonStyle(.bordered)
            }
        }
        .padding(.vertical, 4)
    }

    static func fmt(_ v: Double?) -> String {
        guard let v else { return "-" }
        return v == v.rounded() ? String(Int(v)) : String(format: "%.3g", v)
    }
}
