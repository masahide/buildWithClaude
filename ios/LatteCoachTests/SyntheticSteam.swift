import Foundation
@testable import LatteCoach

/// テスト用の合成スチーム音。実際の録音（log/2026-11-05）の並びをまねる:
/// 背景3秒 → 空だし1秒 → 物音5秒 → 始めのキュルルル（3.5 kHz の甲高い音）→ 泡入れ（音量が細かく上下する雑音）
/// → 渦（背景より数 dB 大きいだけの滑らかな雑音。bursts 回だけ中域の破裂）→ 終わりのキュルキュル（1.3 kHz）→ 無音3秒
enum SyntheticSteam {
    static let sampleRate = 48_000.0

    static func frames(squealSec: Double, airSec: Double, stirSec: Double, bursts: Int, purgeOnly: Bool = false) -> [BandFrame] {
        var rng = SeededRandom(seed: 42)
        var samples: [Float] = []
        samples += noise(sec: 3, amp: 0.002, rng: &rng)
        samples += noise(sec: 1, amp: 0.3, rng: &rng)           // 空だし
        samples += noise(sec: 5, amp: 0.0025, rng: &rng)        // 物音
        if !purgeOnly {
            samples += tone(sec: squealSec, hz: 3500, amp: 0.3, floor: 0.002, rng: &rng)
            samples += aeration(sec: airSec, rng: &rng)
            samples += stir(sec: stirSec, bursts: bursts, rng: &rng)
            samples += tone(sec: 2, hz: 1300, amp: 0.05, floor: 0.0032, rng: &rng)
        }
        samples += noise(sec: 3, amp: 0.001, rng: &rng)
        return BandAnalyzer(sampleRate: sampleRate).append(samples)
    }

    /// 背景音はアプリと同じく、先頭3秒の中央値
    static func background(_ frames: [BandFrame]) -> Float {
        let head = frames.prefix(30).map(\.total).sorted()
        return head[head.count / 2]
    }

    static func run(squealSec: Double = 4, airSec: Double, stirSec: Double, bursts: Int, purgeOnly: Bool = false) -> CupFeatures? {
        let f = frames(squealSec: squealSec, airSec: airSec, stirSec: stirSec, bursts: bursts, purgeOnly: purgeOnly)
        return FeatureExtractor.extract(frames: f, background: background(f))
    }

    private static func noise(sec: Double, amp: Float, rng: inout SeededRandom) -> [Float] {
        (0..<Int(sec * sampleRate)).map { _ in amp * rng.nextSigned() }
    }

    private static func tone(sec: Double, hz: Double, amp: Float, floor: Float, rng: inout SeededRandom) -> [Float] {
        (0..<Int(sec * sampleRate)).map { i in
            amp * Float(sin(2 * .pi * hz * Double(i) / sampleRate)) + floor * rng.nextSigned()
        }
    }

    /// 0.1〜0.3 秒ごとに音量が大きく変わる雑音（ジュルジュル）
    private static func aeration(sec: Double, rng: inout SeededRandom) -> [Float] {
        let n = Int(sec * sampleRate)
        var out: [Float] = []
        out.reserveCapacity(n)
        while out.count < n {
            let len = Int((0.1 + 0.2 * Double(abs(rng.nextSigned()))) * sampleRate)
            let amp: Float = 0.02 + 0.2 * abs(rng.nextSigned())
            for _ in 0..<min(len, n - out.count) { out.append(amp * rng.nextSigned()) }
        }
        return out
    }

    /// 背景より約 +4 dB の滑らかな雑音（渦）。bursts 回だけ 0.2 秒の中域の破裂（実際の録音と同じく +10 dB ほど）を入れる
    private static func stir(sec: Double, bursts: Int, rng: inout SeededRandom) -> [Float] {
        let n = Int(sec * sampleRate)
        var out = (0..<n).map { _ in 0.0032 * rng.nextSigned() }
        guard bursts > 0 else { return out }
        let burstLen = Int(0.2 * sampleRate)
        for b in 0..<bursts {
            let start = n * (b + 1) / (bursts + 1)
            for i in start..<min(n, start + burstLen) {
                out[i] += Float(0.012 * sin(2 * .pi * 900 * Double(i) / sampleRate))
            }
        }
        return out
    }
}

struct SeededRandom {
    private var state: UInt64
    init(seed: UInt64) { state = seed }
    mutating func nextSigned() -> Float {
        state = state &* 6364136223846793005 &+ 1442695040888963407
        return Float(Int64(bitPattern: state >> 1) % 2_000_001) / 1_000_000 - 1
    }
}
