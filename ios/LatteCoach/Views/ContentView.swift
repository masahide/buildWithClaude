import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var practice: PracticeSession
    @EnvironmentObject private var store: CupStore
    @EnvironmentObject private var sender: CupSenderBox
    @State private var capturing: Cup?

    var body: some View {
        NavigationStack {
            List {
                Section { PracticeControls(onCut: cut) }
                Section("杯") {
                    if store.cups.isEmpty {
                        Text("まだ杯がありません").foregroundStyle(.secondary)
                    }
                    ForEach(store.cups) { cup in
                        CupRow(cup: cup) { Task { await sender.sender.send(cup.id) } }
                    }
                }
            }
            .navigationTitle("スチームコーチ")
            .sheet(item: $capturing) { cup in CupCaptureView(cup: cup) }
            .alert("エラー", isPresented: Binding(get: { practice.errorMessage != nil },
                                                set: { if !$0 { practice.errorMessage = nil } })) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(practice.errorMessage ?? "")
            }
        }
    }

    private func cut() {
        let cup = practice.cutCup()
        store.add(cup)
        capturing = cup
    }
}

private struct PracticeControls: View {
    @EnvironmentObject private var practice: PracticeSession
    var onCut: () -> Void

    var body: some View {
        switch practice.phase {
        case .idle:
            Button {
                Task { await practice.start() }
            } label: {
                Label("練習を開始", systemImage: "mic.fill").frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            Text("開始したらスマホは手元の邪魔にならない所に置いてください。ロックしても録音は続きます。")
                .font(.footnote).foregroundStyle(.secondary)
        case .calibrating:
            HStack {
                ProgressView()
                Text("背景の音を測っています。少し静かに…")
            }
        case .listening:
            LevelMeter(db: practice.levelDb)
            if practice.steamDetected {
                Label("スチームが終わりました。注ぎ終わったら撮ってください", systemImage: "checkmark.circle")
                    .foregroundStyle(.green)
            } else {
                Label("聴いています", systemImage: "waveform").foregroundStyle(.secondary)
            }
            Button(action: onCut) {
                Label("この杯を区切って撮る", systemImage: "camera.fill").frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            Button("練習を終了", role: .destructive) { practice.stop() }
        }
    }
}

private struct LevelMeter: View {
    var db: Double
    var body: some View {
        // 背景音比 0〜40 dB を 0〜1 に。置き場所が遠すぎないかの目安
        let v = min(max(db / 40, 0), 1)
        VStack(alignment: .leading, spacing: 4) {
            ProgressView(value: v).tint(v > 0.2 ? .orange : .gray)
            Text(String(format: "背景音比 %+.0f dB", db)).font(.caption).monospacedDigit().foregroundStyle(.secondary)
        }
    }
}

private struct CupRow: View {
    let cup: Cup
    var onResend: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(cup.endedAt, format: .dateTime.month().day().hour().minute())
                Spacer()
                Text(statusText).font(.caption).foregroundStyle(.secondary)
            }
            if let d = cup.diagnosis {
                if let v = d.previousVerdict { Text("前の杯の予測: \(v)").font(.caption) }
                Text("原因: \(d.process)").bold()
                Text("次の1杯: \(d.fix)")
                Text("起きるはずの変化: \(d.prediction)").foregroundStyle(.secondary)
            } else if let f = cup.features {
                Text(String(format: "スチーム %.0f秒・エア入れ %.0f%%・破裂音 %d回",
                            f.steamDurationSec, f.airPhaseRatio * 100, f.burstCount))
                    .font(.caption).monospacedDigit()
            } else {
                Text("スチーム区間が見つかりませんでした").font(.caption).foregroundStyle(.secondary)
            }
            if let e = cup.errorMessage { Text(e).font(.caption).foregroundStyle(.red) }
            if cup.status == .failed || (cup.status == .ready && cup.photoFilename != nil) {
                Button("送り直す", action: onResend).font(.caption).buttonStyle(.bordered)
            }
        }
    }

    private var statusText: String {
        switch cup.status {
        case .awaitingPhoto: "写真待ち"
        case .ready: "未送信"
        case .sending: "送信中"
        case .diagnosing: "診断中"
        case .done: "診断済み"
        case .failed: "失敗"
        }
    }
}
