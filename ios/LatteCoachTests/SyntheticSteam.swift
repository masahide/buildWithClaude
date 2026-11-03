import Foundation
@testable import LatteCoach

/// テスト用の合成スチーム音。背景3秒 → エア入れ（高域のノイズ）→ 撹拌（低中域）→ 無音2秒。
enum SyntheticSteam {
    static let sampleRate = 48_000.0

    static func run(airSec: Double, stirSec: Double, bursts: Int) -> CupFeatures? {
        var rng = SeededRandom(seed: 42)
        var samples: [Float] = []
        samples += noise(sec: 3, amp: 0.002, rng: &rng)
        samples += highHiss(sec: airSec, rng: &rng)
        samples += stir(sec: stirSec, bursts: bursts, rng: &rng)
        samples += noise(sec: 2, amp: 0.002, rng: &rng)

        let analyzer = BandAnalyzer(sampleRate: sampleRate)
        let frames = analyzer.append(samples)
        let backgroundFrames = Array(frames.prefix(30))
        let background = backgroundFrames.map(\.total).sorted()[backgroundFrames.count / 2]
        return FeatureExtractor.extract(frames: frames, background: background)
    }

    private static func noise(sec: Double, amp: Float, rng: inout SeededRandom) -> [Float] {
        (0..<Int(sec * sampleRate)).map { _ in amp * rng.nextSigned() }
    }

    /// 白色雑音を一次差分して高域を強調する（紙を裂く音の代わり）
    private static func highHiss(sec: Double, rng: inout SeededRandom) -> [Float] {
        var prev: Float = 0
        return (0..<Int(sec * sampleRate)).map { _ in
            let x = 0.3 * rng.nextSigned()
            defer { prev = x }
            return x - prev
        }
    }

    /// 低域の正弦波＋弱い雑音（渦の静かな轟音の代わり）。bursts 回だけ 0.2 秒の中域の破裂を入れる
    private static func stir(sec: Double, bursts: Int, rng: inout SeededRandom) -> [Float] {
        let n = Int(sec * sampleRate)
        var out = (0..<n).map { i -> Float in
            let t = Double(i) / sampleRate
            return Float(0.15 * sin(2 * .pi * 180 * t)) + 0.01 * rng.nextSigned()
        }
        guard bursts > 0 else { return out }
        let burstLen = Int(0.2 * sampleRate)
        for b in 0..<bursts {
            let start = n * (b + 1) / (bursts + 1)
            for i in start..<min(n, start + burstLen) {
                let t = Double(i) / sampleRate
                out[i] += Float(0.6 * sin(2 * .pi * 900 * t))
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
