import Accelerate
import Foundation

/// 0.1 秒ごとの3帯域エネルギー。生の音声は保持せず、これだけをメモリに残す。
struct BandFrame: Codable, Equatable {
    var low: Float   // 50–400 Hz: こもった轟音（ノズルが深すぎる疑い）
    var mid: Float   // 400–2000 Hz: ゴボゴボ（大きな泡の破裂）
    var high: Float  // 2000–8000 Hz: 紙を裂く音（エア入れ）
    var total: Float { low + mid + high }
}

/// 1杯ぶんのスカラー特徴量。すべて相対値（背景音・区間内の比）にして端末差・置き場所の差に耐える。
struct CupFeatures: Codable, Equatable {
    /// スチーム区間の長さ（秒）
    var steamDurationSec: Double
    /// スチーム区間のうちエア入れ相が占める割合（0〜1）
    var airPhaseRatio: Double
    /// エア入れ相から撹拌相へ移った位置（区間の先頭からの割合 0〜1）。現状は airPhaseRatio と同値
    var transitionAt: Double
    /// 撹拌相の音の安定度（1 − 変動係数、0〜1。大きいほど安定）
    var stirStability: Double
    /// 撹拌相の低域比率（0〜1）
    var stirLowBandRatio: Double
    /// 撹拌相の大きな泡の破裂音の回数
    var burstCount: Int
    /// スチーム区間の音量の背景音比（dB）。置き場所の目安として記録する
    var levelOverBackgroundDb: Double

    enum CodingKeys: String, CodingKey {
        case steamDurationSec = "steam_duration_sec"
        case airPhaseRatio = "air_phase_ratio"
        case transitionAt = "transition_at"
        case stirStability = "stir_stability"
        case stirLowBandRatio = "stir_low_band_ratio"
        case burstCount = "burst_count"
        case levelOverBackgroundDb = "level_over_background_db"
    }
}

/// 帯域エネルギーの計算（サンプル列 → 0.1 秒ごとの BandFrame）。
final class BandAnalyzer {
    static let frameDuration = 0.1

    let sampleRate: Double
    private let samplesPerFrame: Int
    private let fftSize = 4096
    private let fft: vDSP.FFT<DSPSplitComplex>
    private let window: [Float]
    private var pending: [Float] = []

    init(sampleRate: Double) {
        self.sampleRate = sampleRate
        samplesPerFrame = Int(sampleRate * Self.frameDuration)
        fft = vDSP.FFT(log2n: vDSP_Length(log2(Double(fftSize))), radix: .radix2, ofType: DSPSplitComplex.self)!
        window = vDSP.window(ofType: Float.self, usingSequence: .hanningDenormalized, count: fftSize, isHalfWindow: false)
    }

    /// サンプルを足し込み、0.1 秒ぶん溜まるごとにフレームを返す。
    func append(_ samples: [Float]) -> [BandFrame] {
        pending.append(contentsOf: samples)
        var frames: [BandFrame] = []
        while pending.count >= samplesPerFrame {
            frames.append(analyze(Array(pending[0..<samplesPerFrame])))
            pending.removeFirst(samplesPerFrame)
        }
        return frames
    }

    private func analyze(_ frame: [Float]) -> BandFrame {
        var input = [Float](repeating: 0, count: fftSize)
        let n = min(frame.count, fftSize)
        input.replaceSubrange(0..<n, with: frame[0..<n])
        input = vDSP.multiply(input, window)

        let half = fftSize / 2
        var real = [Float](repeating: 0, count: half)
        var imag = [Float](repeating: 0, count: half)
        var power = [Float](repeating: 0, count: half)
        real.withUnsafeMutableBufferPointer { rp in
            imag.withUnsafeMutableBufferPointer { ip in
                var split = DSPSplitComplex(realp: rp.baseAddress!, imagp: ip.baseAddress!)
                input.withUnsafeBytes { raw in
                    vDSP_ctoz(raw.bindMemory(to: DSPComplex.self).baseAddress!, 2, &split, 1, vDSP_Length(half))
                }
                fft.forward(input: split, output: &split)
                vDSP.squareMagnitudes(split, result: &power)
            }
        }

        let binHz = sampleRate / Double(fftSize)
        func band(_ lo: Double, _ hi: Double) -> Float {
            let a = max(1, Int(lo / binHz)), b = min(half - 1, Int(hi / binHz))
            guard b > a else { return 0 }
            return vDSP.sum(power[a...b]) / Float(fftSize)
        }
        return BandFrame(low: band(50, 400), mid: band(400, 2000), high: band(2000, 8000))
    }
}

/// 閾値。家庭の録音で調整する前提の暫定値。
struct FeatureThresholds {
    /// 背景音の何倍をスチームとみなすか（6 で約 +8 dB）
    var steamOverBackground: Float = 6
    /// この秒数より短い途切れはスチーム区間に統合する（空ぶかしなど）
    var mergeGapSec: Double = 1.5
    /// この秒数に満たない区間は弾く（グラインダー、ケトルなど）
    var minSteamSec: Double = 8
    /// スチーム後、この秒数静かならスチーム終了とみなす（通知用）
    var endSilenceSec: Double = 2
    /// 撹拌相の中央値の何倍を破裂音とみなすか
    var burstOverMedian: Float = 1.8
}

enum FeatureExtractor {
    /// 1杯ぶんのフレーム列からスチーム区間を探し、特徴量を計算する。区間が見つからなければ nil。
    static func extract(frames: [BandFrame], background: Float, thresholds t: FeatureThresholds = .init()) -> CupFeatures? {
        guard let range = longestSteamRange(frames: frames, background: background, thresholds: t) else { return nil }
        let steam = Array(frames[range])
        let n = steam.count

        // エア入れ相: 高域比率（1 秒移動平均）が、区間内の高低の中点を最後に上回った位置まで
        let highRatio = steam.map { $0.total > 0 ? $0.high / $0.total : 0 }
        let smooth = movingAverage(highRatio, width: Int(1 / BandAnalyzer.frameDuration))
        let sorted = smooth.sorted()
        let p10 = sorted[n / 10], p90 = sorted[min(n - 1, n * 9 / 10)]
        let mid = (p10 + p90) / 2
        // エア入れはスチームの前半で終わる前提で、前 70% の中から探す
        let searchEnd = max(1, n * 7 / 10)
        var transition = 0
        if p90 - p10 > 0.05 {
            for i in 0..<searchEnd where smooth[i] >= mid { transition = i + 1 }
        }
        let airRatio = Double(transition) / Double(n)

        let stir = Array(steam[min(transition, n - 1)...])
        let stirTotals = stir.map(\.total)
        let mean = vDSP.mean(stirTotals)
        let std = sqrt(vDSP.meanSquare(vDSP.add(-mean, stirTotals)))
        let stability = mean > 0 ? Double(max(0, min(1, 1 - std / mean))) : 0
        let stirSum = stirTotals.reduce(0, +)
        let lowRatio = stirSum > 0 ? Double(stir.map(\.low).reduce(0, +) / stirSum) : 0

        // 破裂音: 中低域が撹拌相の中央値を大きく超えた立ち上がりを数える
        let midLow = stir.map { $0.mid + $0.low }
        let median = midLow.sorted()[midLow.count / 2]
        var bursts = 0
        var above = false
        for v in midLow {
            let now = v > median * t.burstOverMedian
            if now && !above { bursts += 1 }
            above = now
        }

        let steamMedian = steam.map(\.total).sorted()[n / 2]
        let levelDb = background > 0 ? 10 * log10(Double(steamMedian / background)) : 0

        return CupFeatures(
            steamDurationSec: Double(n) * BandAnalyzer.frameDuration,
            airPhaseRatio: round3(airRatio),
            transitionAt: round3(airRatio),
            stirStability: round3(stability),
            stirLowBandRatio: round3(lowRatio),
            burstCount: bursts,
            levelOverBackgroundDb: round3(levelDb)
        )
    }

    /// 途切れを統合したうえで最長のスチーム区間を返す。
    static func longestSteamRange(frames: [BandFrame], background: Float, thresholds t: FeatureThresholds) -> Range<Int>? {
        let threshold = max(background, 1e-12) * t.steamOverBackground
        let maxGap = Int(t.mergeGapSec / BandAnalyzer.frameDuration)
        var runs: [Range<Int>] = []
        var start: Int?
        var lastLoud = -1
        for (i, f) in frames.enumerated() {
            guard f.total > threshold else { continue }
            if let s = start, i - lastLoud > maxGap + 1 {
                runs.append(s..<(lastLoud + 1))
                start = i
            } else if start == nil {
                start = i
            }
            lastLoud = i
        }
        if let s = start { runs.append(s..<(lastLoud + 1)) }
        let minFrames = Int(t.minSteamSec / BandAnalyzer.frameDuration)
        return runs.filter { $0.count >= minFrames }.max { $0.count < $1.count }
    }

    private static func movingAverage(_ x: [Float], width: Int) -> [Float] {
        guard width > 1, x.count > 0 else { return x }
        var out = [Float](repeating: 0, count: x.count)
        var acc: Float = 0
        for i in 0..<x.count {
            acc += x[i]
            if i >= width { acc -= x[i - width] }
            out[i] = acc / Float(min(i + 1, width))
        }
        return out
    }

    private static func round3(_ v: Double) -> Double { (v * 1000).rounded() / 1000 }
}

/// スチームの鳴り終わりを逐次判定する（区間終了の通知用）。杯の区切りは手動ボタンで行う。
struct SteamEndDetector {
    var thresholds = FeatureThresholds()
    private var loudFrames = 0
    private var quietFrames = 0
    private var fired = false

    init(thresholds: FeatureThresholds = .init()) { self.thresholds = thresholds }

    /// スチームが一定時間続いた後に静かになった瞬間だけ true を返す。
    mutating func feed(_ frame: BandFrame, background: Float) -> Bool {
        let loud = frame.total > max(background, 1e-12) * thresholds.steamOverBackground
        let gapFrames = Int(thresholds.mergeGapSec / BandAnalyzer.frameDuration)
        if loud {
            loudFrames += 1
            quietFrames = 0
            return false
        }
        quietFrames += 1
        // 空ぶかしなどの短い途切れは続きとみなす
        if quietFrames > gapFrames && loudFrames < Int(thresholds.minSteamSec / BandAnalyzer.frameDuration) {
            loudFrames = 0
        }
        if !fired, loudFrames >= Int(thresholds.minSteamSec / BandAnalyzer.frameDuration),
           quietFrames >= Int(thresholds.endSilenceSec / BandAnalyzer.frameDuration) {
            fired = true
            return true
        }
        return false
    }

    /// 杯を区切ったら次の杯に備えて戻す。
    mutating func reset() {
        loudFrames = 0
        quietFrames = 0
        fired = false
    }
}
