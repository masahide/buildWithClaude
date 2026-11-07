import Foundation
import UIKit

/// 杯の記録を端末内（Documents）に保存する。保存するのは特徴量と写真だけで、音声は保存しない。
@MainActor
final class CupStore: ObservableObject {
    @Published private(set) var cups: [Cup] = []

    private let dir: URL
    private var indexURL: URL { dir.appendingPathComponent("cups.json") }

    init() {
        dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Cups", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        if let data = try? Data(contentsOf: indexURL),
           let saved = try? JSONDecoder.iso.decode([Cup].self, from: data) {
            cups = saved
        }
    }

    func add(_ cup: Cup) {
        cups.insert(cup, at: 0)
        save()
    }

    func update(_ id: UUID, _ change: (inout Cup) -> Void) {
        guard let i = cups.firstIndex(where: { $0.id == id }) else { return }
        change(&cups[i])
        save()
    }

    func cup(_ id: UUID) -> Cup? { cups.first { $0.id == id } }

    func savePhoto(_ image: UIImage, for id: UUID) -> String? {
        guard let data = image.resizedForUpload().jpegData(compressionQuality: 0.8) else { return nil }
        let name = "\(id.uuidString).jpg"
        do {
            try data.write(to: dir.appendingPathComponent(name))
            return name
        } catch {
            return nil
        }
    }

    /// 送る前の音を一時保存する（送れたら deleteFile で消す）
    func saveAudio(_ data: Data, for id: UUID) -> String? {
        let name = "\(id.uuidString).wav"
        do {
            try data.write(to: dir.appendingPathComponent(name))
            return name
        } catch {
            return nil
        }
    }

    func fileData(_ filename: String) -> Data? {
        try? Data(contentsOf: dir.appendingPathComponent(filename))
    }

    func deleteFile(_ filename: String) {
        try? FileManager.default.removeItem(at: dir.appendingPathComponent(filename))
    }

    func photoData(_ filename: String) -> Data? {
        try? Data(contentsOf: dir.appendingPathComponent(filename))
    }

    private func save() {
        if let data = try? JSONEncoder.iso.encode(cups) {
            try? data.write(to: indexURL, options: .atomic)
        }
    }
}

extension JSONEncoder {
    static let iso: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()
}

extension JSONDecoder {
    static let iso: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()
}

extension UIImage {
    /// 長辺 1600px に縮める（泡の粒が読める程度に残し、送信量を抑える）
    func resizedForUpload(maxSide: CGFloat = 1600) -> UIImage {
        let longest = max(size.width, size.height)
        guard longest > maxSide else { return self }
        let scale = maxSide / longest
        let target = CGSize(width: size.width * scale, height: size.height * scale)
        return UIGraphicsImageRenderer(size: target).image { _ in draw(in: CGRect(origin: .zero, size: target)) }
    }
}
