import Accelerate
import Foundation

/// 0.1 秒ごとの3帯域エネルギー。生の音声は保持せず、これだけをメモリに残す。
struct BandFrame: Codable, Equatable {
    var low: Float   // 50–400 Hz: こもった轟音（ノズルが深すぎる疑い）
    var mid: Float   // 400–2000 Hz: ジュルジュル・ゴボゴボ
    var high: Float  // 2000–8000 Hz: 始めの「キュルルル」、空だし
    var total: Float { low + mid + high }
}

/// 1杯ぶんのスカラー特徴量。すべて相対値（背景音・区間内の比）にして端末差・置き場所の差に耐える。
///
/// 実際のスチームの音の並び（log/2026-11-05）:
/// 空だし（1 秒ほど）→ 物音 → 始めの「キュルルル」（高域に集中した甲高い音）→ 泡入れの「ジュルジュル」
/// （音量が細かく上下する）→ 渦（静かで滑らか。背景より数 dB 大きいだけ）→ 終わりの「キュルキュル」→ 止める
struct CupFeatures: Codable, Equatable {
    /// スチーム区間の長さ（秒）。蒸気を出してから止めるまで。空だしは含まない
    var steamDurationSec: Double
    /// 始めの「キュルルル」の長さ（秒）
    var startSquealSec: Double
    /// スチーム区間のうち、泡入れ（ジュルジュル）が占める割合（0〜1）。追加の泡入れも含み、始めのキュルルルは含まない
    var airPhaseRatio: Double
    /// 最初の泡入れの長さ（秒）
    var firstAirSec: Double
    /// 一度渦に入ってから追加で泡入れした回数
    var reAirCount: Int
    /// 追加の泡入れの合計の長さ（秒）
    var reAirSec: Double
    /// 最後の泡入れから渦（撹拌）へ移った位置（区間の先頭からの割合 0〜1）
    var transitionAt: Double
    /// 撹拌相の音の滑らかさ（1 / (1 + 音量の揺れの dB)。1 に近いほど滑らか）
    var stirStability: Double
    /// 撹拌相の低域比率（0〜1）
    var stirLowBandRatio: Double
    /// 撹拌相で中域が急に大きくなった回数（ゴボゴボ）
    var burstCount: Int
    /// スチーム区間の音量の背景音比（dB、中央値）。置き場所の目安として記録する
    var levelOverBackgroundDb: Double

    enum CodingKeys: String, CodingKey {
        case steamDurationSec = "steam_duration_sec"
        case startSquealSec = "start_squeal_sec"
        case airPhaseRatio = "air_phase_ratio"
        case firstAirSec = "first_air_sec"
        case reAirCount = "re_air_count"
        case reAirSec = "re_air_sec"
        case transitionAt = "transition_at"
        case stirStability = "stir_stability"
        case stirLowBandRatio = "stir_low_band_ratio"
        case burstCount = "burst_count"
        case levelOverBackgroundDb = "level_over_background_db"
    }
}

extension CupFeatures {
    /// 11-07 より前の版で保存した杯には、キュルルル・泡入れの区間の値がない。読めなくならないよう 0 で埋める
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        steamDurationSec = try c.decode(Double.self, forKey: .steamDurationSec)
        startSquealSec = try c.decodeIfPresent(Double.self, forKey: .startSquealSec) ?? 0
        airPhaseRatio = try c.decode(Double.self, forKey: .airPhaseRatio)
        firstAirSec = try c.decodeIfPresent(Double.self, forKey: .firstAirSec) ?? 0
        reAirCount = try c.decodeIfPresent(Int.self, forKey: .reAirCount) ?? 0
        reAirSec = try c.decodeIfPresent(Double.self, forKey: .reAirSec) ?? 0
        transitionAt = try c.decode(Double.self, forKey: .transitionAt)
        stirStability = try c.decode(Double.self, forKey: .stirStability)
        stirLowBandRatio = try c.decode(Double.self, forKey: .stirLowBandRatio)
        burstCount = try c.decode(Int.self, forKey: .burstCount)
        levelOverBackgroundDb = try c.decode(Double.self, forKey: .levelOverBackgroundDb)
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

/// スチームの長さに比例する長さ（秒）。下限と上限で挟む
struct Scaled {
    var fraction: Double
    var min: Double
    var max: Double
    func seconds(forSteam steamSec: Double) -> Double { Swift.min(max, Swift.max(min, fraction * steamSec)) }
}

/// 閾値。11-05 のボイスメモ1本で合わせた暫定値（log/2026-11-05）。
struct FeatureThresholds {
    /// 始まりの判定: 1 秒平均の音量が背景よりこの dB を超えた状態が onsetSustainSec 続いたら、スチームが始まったとみなす。
    /// 空だし（1 秒ほど）は続かないので弾かれる
    var onsetDb: Float = 10
    var onsetSustainSec: Double = 2
    /// 続きの判定: 1 秒平均の音量がこの dB を下回った状態が endQuietSec 続いたら、スチームが終わったとみなす。
    /// 渦の撹拌相は背景より +2〜5 dB しかないので、低めにする
    var stayDb: Float = 1.5
    var endQuietSec: Double = 2
    /// この秒数に満たない区間は弾く
    var minSteamSec: Double = 8
    /// 始めのキュルルル: 区間の先頭で、高域の割合がこれ以上の間
    var squealHighRatio: Float = 0.9
    // 以下の3つはスチームの長さに比例させる（家庭用でも 15 秒ほどで終わるマシンから 60 秒かかるマシンまである。log/2026-11-07）。
    // 割合と、下限・上限の秒。上限は 11-05 の録音（56 秒）で合わせた値
    /// 泡入れの途中のこの長さ以下の途切れはつなぐ
    var airGap = Scaled(fraction: 0.03, min: 0.7, max: 1.5)
    /// この長さに満たない「揺れの大きい区間」は泡入れに数えない（渦の中のゴボゴボ）
    var minAir = Scaled(fraction: 0.05, min: 1.5, max: 2.5)
    /// 止める間際の「キュルキュル」。撹拌相の値を測るときは末尾のこの長さを除く
    var endSqueal = Scaled(fraction: 0.06, min: 1, max: 3)
    /// 破裂音: 撹拌相の中域が、その中央値よりこの dB 以上大きくなった立ち上がり
    var burstOverMedianDb: Float = 6
}

enum FeatureExtractor {
    static let framesPerSecond = Int((1 / BandAnalyzer.frameDuration).rounded())

    /// 1杯ぶんのフレーム列からスチーム区間を探し、特徴量を計算する。区間が見つからなければ nil。
    static func extract(frames: [BandFrame], background: Float, thresholds t: FeatureThresholds = .init()) -> CupFeatures? {
        guard let range = longestSteamRange(frames: frames, background: background, thresholds: t) else { return nil }
        let steam = Array(frames[range])
        let n = steam.count
        let bg = max(background, 1e-12)
        let db = steam.map { 10 * log10(max($0.total, 1e-12) / bg) }

        // 始めのキュルルル: 先頭から、高域の割合（0.5 秒平均）が高い間
        let highRatio = movingAverage(steam.map { $0.total > 0 ? $0.high / $0.total : 0 }, width: framesPerSecond / 2)
        // 区間の始まりは音が立ち上がる途中なので、先頭 2 秒以内に始まるひと続きを探す
        var squealEnd = 0
        var squealStart = 0
        if let first = (0..<min(n, 2 * framesPerSecond)).first(where: { highRatio[$0] >= t.squealHighRatio }) {
            squealStart = first
            squealEnd = first
            while squealEnd < min(n, 10 * framesPerSecond) && highRatio[squealEnd] >= t.squealHighRatio { squealEnd += 1 }
        }

        // 泡入れ（ジュルジュル）は音量が細かく上下し、渦に入ると滑らかになる。
        // 泡入れは1回とは限らない。一度渦に入ってから、泡が足りないと思って追加で泡入れすることがある（log/2026-11-06）。
        // 音量の揺れ（±0.5 秒の標準偏差、中心の 1 秒平均）が区間内の高低の中点を超える区間を泡入れとし、airGap 以下の途切れはつなぐ。
        // minAir に満たない区間は、渦の中のゴボゴボ（短い破裂）とみなして泡入れに数えない
        // 揺れは ±0.5 秒の標準偏差（中心の 1 秒平均）。変化の中央値で測る案は、短い合成音では良くなったが、
        // 11-05 の実際の録音で追加の泡入れの終わりを 2 秒早く切ったので採らない（log/2026-11-07）
        let jitter = centeredAverage((0..<n).map { i in std(db[max(0, i - framesPerSecond / 2)..<min(n, i + framesPerSecond / 2)]) },
                                     width: framesPerSecond)
        let steamSec = Double(n) * BandAnalyzer.frameDuration
        let endSquealFrames = Int(t.endSqueal.seconds(forSteam: steamSec) * Double(framesPerSecond))
        let fitEnd = max(squealEnd + 2, n - endSquealFrames)
        let airSegments = segments(Array(jitter[squealEnd..<fitEnd]),
                                   maxGap: Int(t.airGap.seconds(forSteam: steamSec) * Double(framesPerSecond)),
                                   minLength: Int(t.minAir.seconds(forSteam: steamSec) * Double(framesPerSecond)))
            .map { ($0.lowerBound + squealEnd)..<($0.upperBound + squealEnd) }
        // 渦への境は、最後の泡入れの終わり
        let transition = airSegments.last?.upperBound ?? squealEnd
        let airFrames = airSegments.map(\.count).reduce(0, +)

        // 撹拌相の値は、止める間際の「キュルキュル」（末尾 endSqueal）を除いて測る
        let stirEnd = max(min(transition, n - 1) + 1, n - endSquealFrames)
        let stirRange = min(transition, n - 1)..<stirEnd
        let stirDb = Array(db[stirRange])
        let stability = 1 / (1 + Double(std(stirDb[...])))
        let stir = steam[stirRange]
        let stirSum = stir.map(\.total).reduce(0, +)
        let lowRatio = stirSum > 0 ? Double(stir.map(\.low).reduce(0, +) / stirSum) : 0

        // 境の直後は泡入れの名残が混ざるので、破裂音は境から 1 秒後より数える
        let midDb = stir.dropFirst(min(framesPerSecond, max(0, stir.count - 1))).map { 10 * log10(max($0.mid, 1e-12)) }
        let midMedian = midDb.sorted()[midDb.count / 2]
        var bursts = 0
        var above = false
        for v in midDb {
            let now = v > midMedian + t.burstOverMedianDb
            if now && !above { bursts += 1 }
            above = now
        }

        return CupFeatures(
            steamDurationSec: round3(Double(n) * BandAnalyzer.frameDuration),
            startSquealSec: round3(Double(squealEnd - squealStart) * BandAnalyzer.frameDuration),
            airPhaseRatio: round3(Double(airFrames) / Double(n)),
            firstAirSec: round3(Double(airSegments.first?.count ?? 0) * BandAnalyzer.frameDuration),
            reAirCount: max(0, airSegments.count - 1),
            reAirSec: round3(Double(airSegments.dropFirst().map(\.count).reduce(0, +)) * BandAnalyzer.frameDuration),
            transitionAt: round3(Double(transition) / Double(n)),
            stirStability: round3(stability),
            stirLowBandRatio: round3(lowRatio),
            burstCount: bursts,
            levelOverBackgroundDb: round3(Double(db.sorted()[n / 2]))
        )
    }

    /// 1 秒平均の音量（背景音比 dB）にヒステリシスをかけて、最長のスチーム区間を返す。
    static func longestSteamRange(frames: [BandFrame], background: Float, thresholds t: FeatureThresholds) -> Range<Int>? {
        let bg = max(background, 1e-12)
        let level = centeredAverage(frames.map { 10 * log10(max($0.total, 1e-12) / bg) }, width: framesPerSecond)
        let sustain = Int(t.onsetSustainSec * Double(framesPerSecond))
        let endQuiet = Int(t.endQuietSec * Double(framesPerSecond))
        var runs: [Range<Int>] = []
        var start: Int?
        var aboveRun = 0
        var quiet = 0
        for (i, v) in level.enumerated() {
            if let s = start {
                quiet = v < t.stayDb ? quiet + 1 : 0
                if quiet >= endQuiet {
                    runs.append(s..<(i - quiet + 1))
                    start = nil
                    aboveRun = 0
                }
            } else {
                aboveRun = v > t.onsetDb ? aboveRun + 1 : 0
                if aboveRun >= sustain {
                    start = i - sustain + 1
                    quiet = 0
                }
            }
        }
        if let s = start { runs.append(s..<(level.count - quiet)) }
        let minFrames = Int(t.minSteamSec * Double(framesPerSecond))
        return runs.filter { $0.count >= minFrames }.max { $0.count < $1.count }
    }

    /// 列が区間内の高低（10% 点と 90% 点）の中点を超える区間を返す。maxGap 以下の途切れはつなぎ、minLength 未満は捨てる
    static func segments(_ x: [Float], maxGap: Int, minLength: Int) -> [Range<Int>] {
        guard x.count > 1 else { return [] }
        let sorted = x.sorted()
        let p10 = sorted[x.count / 10], p90 = sorted[min(x.count - 1, x.count * 9 / 10)]
        guard p90 - p10 > 0.5 else { return [] }
        let mid = (p10 + p90) / 2
        var raw: [Range<Int>] = []
        var start: Int?
        for (i, v) in x.enumerated() {
            if v >= mid { if start == nil { start = i } } else if let s = start { raw.append(s..<i); start = nil }
        }
        if let s = start { raw.append(s..<x.count) }
        var merged: [Range<Int>] = []
        for r in raw {
            if let last = merged.last, r.lowerBound - last.upperBound <= maxGap {
                merged[merged.count - 1] = last.lowerBound..<r.upperBound
            } else {
                merged.append(r)
            }
        }
        return merged.filter { $0.count >= minLength }
    }

    /// 後ろ向きの移動平均（逐次処理と同じ形）
    static func movingAverage(_ x: [Float], width: Int) -> [Float] {
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

    /// 中心の移動平均（区間の端がずれないように）
    static func centeredAverage(_ x: [Float], width: Int) -> [Float] {
        guard width > 1, x.count > 0 else { return x }
        return (0..<x.count).map { i in
            let lo = max(0, i - width / 2), hi = min(x.count, i + width - width / 2)
            return x[lo..<hi].reduce(0, +) / Float(hi - lo)
        }
    }

    static func std(_ x: ArraySlice<Float>) -> Float {
        guard x.count > 1 else { return 0 }
        let m = x.reduce(0, +) / Float(x.count)
        return sqrt(x.reduce(0) { $0 + ($1 - m) * ($1 - m) } / Float(x.count))
    }

    private static func round3(_ v: Double) -> Double { (v * 1000).rounded() / 1000 }
}

/// スチームの鳴り終わりを逐次判定する（区間終了の通知用）。杯の区切りは手動ボタンで行う。
/// 判定は longestSteamRange と同じ（1 秒平均の音量にヒステリシス）。
struct SteamEndDetector {
    var thresholds = FeatureThresholds()
    private var recent: [Float] = []
    private var aboveRun = 0
    private var steamFrames = 0
    private var quietFrames = 0
    private var inSteam = false
    private var fired = false

    init(thresholds: FeatureThresholds = .init()) { self.thresholds = thresholds }

    /// スチームが一定時間続いた後に静かになった瞬間だけ true を返す。
    mutating func feed(_ frame: BandFrame, background: Float) -> Bool {
        let fps = FeatureExtractor.framesPerSecond
        recent.append(10 * log10(max(frame.total, 1e-12) / max(background, 1e-12)))
        if recent.count > fps { recent.removeFirst() }
        let level = recent.reduce(0, +) / Float(recent.count)

        if !inSteam {
            aboveRun = level > thresholds.onsetDb ? aboveRun + 1 : 0
            if aboveRun >= Int(thresholds.onsetSustainSec * Double(fps)) {
                inSteam = true
                steamFrames = aboveRun
                quietFrames = 0
            }
            return false
        }
        steamFrames += 1
        quietFrames = level < thresholds.stayDb ? quietFrames + 1 : 0
        guard quietFrames >= Int(thresholds.endQuietSec * Double(fps)) else { return false }
        inSteam = false
        aboveRun = 0
        let long = Double(steamFrames - quietFrames) >= thresholds.minSteamSec * Double(fps)
        if long && !fired {
            fired = true
            return true
        }
        return false
    }

    /// 杯を区切ったら次の杯に備えて戻す。
    mutating func reset() {
        recent = []
        aboveRun = 0
        steamFrames = 0
        quietFrames = 0
        inSteam = false
        fired = false
    }
}
