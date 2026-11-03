import SwiftUI

/// 区切った杯に、ピッチャーの残りの写真1枚と任意の自己評価を付けて送る。
struct CupCaptureView: View {
    let cup: Cup
    @EnvironmentObject private var store: CupStore
    @EnvironmentObject private var sender: CupSenderBox
    @Environment(\.dismiss) private var dismiss
    @State private var image: UIImage?
    @State private var rating: SelfRating?
    @State private var showCamera = false

    var body: some View {
        NavigationStack {
            Form {
                Section("ピッチャーの残り") {
                    if let image {
                        Image(uiImage: image).resizable().scaledToFit().frame(maxHeight: 280)
                    }
                    Button(image == nil ? "撮る" : "撮り直す") { showCamera = true }
                    Text("注ぎ終わった後に撮ります。カップを並べて写してもかまいません（採点はしません）。")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                Section("自己評価（任意）") {
                    Picker("自己評価", selection: $rating) {
                        Text("なし").tag(SelfRating?.none)
                        ForEach(SelfRating.allCases) { Text($0.rawValue).tag(SelfRating?.some($0)) }
                    }
                    .pickerStyle(.inline)
                    .labelsHidden()
                }
            }
            .navigationTitle("この杯")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("あとで") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("送る") { submit() }.disabled(image == nil)
                }
            }
            .fullScreenCover(isPresented: $showCamera) {
                CameraPicker { image = $0 }.ignoresSafeArea()
            }
            .onAppear { showCamera = true }
        }
    }

    private func submit() {
        let id = cup.id
        let filename = image.flatMap { store.savePhoto($0, for: id) }
        store.update(id) {
            $0.photoFilename = filename
            $0.selfRating = rating
            $0.status = .ready
        }
        Task { await sender.sender.send(id) }
        dismiss()
    }
}

/// EnvironmentObject で CupSender を渡すための入れ物
@MainActor
final class CupSenderBox: ObservableObject {
    let sender: CupSender
    init(store: CupStore) { sender = CupSender(store: store) }
}
