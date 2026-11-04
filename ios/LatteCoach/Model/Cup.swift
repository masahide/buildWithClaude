import Foundation

enum SelfRating: String, Codable, CaseIterable, Identifiable {
    case good = "良かった"
    case tooFoamy = "泡が多すぎた"
    case tooThin = "泡が少なすぎた"
    case coarse = "泡が粗かった"
    var id: String { rawValue }
}

/// コーチの返答。原因の工程1つ・直す点1つ・予測1つ（CLAUDE.md）
struct Diagnosis: Codable, Equatable {
    var process: String              // 「エア入れ」「撹拌」
    var fix: String
    var prediction: String
    var previousVerdict: String?     // 前の杯の予測の当否

    enum CodingKeys: String, CodingKey {
        case process, fix, prediction
        case previousVerdict = "previous_verdict"
    }
}

struct Cup: Codable, Identifiable, Equatable {
    enum Status: String, Codable {
        case awaitingPhoto   // 区切ったが写真がまだ
        case ready           // 写真あり・未送信
        case sending
        case diagnosing      // サーバーが診断中
        case done
        case failed
    }

    var id = UUID()
    var startedAt: Date
    var endedAt: Date
    /// スチーム区間が見つからなかった杯は nil（写真だけ送る）
    var features: CupFeatures?
    /// 区切りまでの帯域エネルギーの包絡（背景音比、0.1 秒ごとの [低, 中, 高]）。
    /// 音声ではなく、会話は復元できない（decisions.md D6）。閾値の調整のためにサーバーへ送る
    var envelope: [[Float]]?
    var selfRating: SelfRating?
    var photoFilename: String?
    var status: Status = .awaitingPhoto
    var serverId: String?
    var diagnosis: Diagnosis?
    var errorMessage: String?
}
