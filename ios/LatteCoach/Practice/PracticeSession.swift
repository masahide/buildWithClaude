import AVFoundation
import Foundation

/// 練習1回ぶんの状態。「開始」→ 置いておく → 杯ごとに「区切って撮る」→「終了」。
@MainActor
final class PracticeSession: ObservableObject {
    enum Phase: Equatable {
        case idle
        case calibrating   // 最初の数秒で背景音を測る
        case listening
    }

    static let calibrationSec = 3.0

    @Published private(set) var phase: Phase = .idle
    @Published private(set) var levelDb: Double = 0       // 背景音比。画面のメーター用
    @Published private(set) var steamDetected = false     // 今の杯でスチームが鳴り終わったか
    @Published private(set) var cupStartedAt = Date()
    @Published var errorMessage: String?

    private let capture = AudioCapture()
    private var background: Float = 0
    private var calibration: [Float] = []
    /// 前回区切ってからのフレーム。帯域エネルギーだけで音声は含まない（30 秒で 300 個）
    private var frames: [BandFrame] = []
    private var endDetector = SteamEndDetector()
    /// 練習の音は、開始から終了まで全部をファイルに書き続け、区切るたびにその区間をサーバーへ送る（D21）。
    /// サーバーで何度でもスチームを切り出し直し、絵を描き直せるように、端末では何も削らない
    private(set) var practiceId = UUID()
    private var segment: WAVWriter?
    private var segmentSeq = 0
    /// 開始からの通しのサンプル番号（今の区間の先頭、書いた合計）と、frames[0] の通しのフレーム番号
    private var segmentStartSample = 0
    private var totalSamples = 0
    private var framesStartFrame = 0
    private var frameCounter = 0
    /// 判定の閾値。練習の開始時にサーバーの今の版を取りに行く（取れなければ既定値）
    private var thresholds = FeatureThresholds()
    @Published private(set) var paramsVersion: Int?
    private var interruptionObserver: NSObjectProtocol?

    init() {
        capture.onFrames = { [weak self] frames, audio in
            Task { @MainActor in self?.consume(frames, audio: audio) }
        }
        interruptionObserver = NotificationCenter.default.addObserver(
            forName: AVAudioSession.interruptionNotification, object: nil, queue: .main
        ) { [weak self] note in
            guard let raw = note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
                  AVAudioSession.InterruptionType(rawValue: raw) == .ended else { return }
            Task { @MainActor in
                if self?.phase != .idle { self?.capture.resumeAfterInterruption() }
            }
        }
    }

    func start() async {
        guard phase == .idle else { return }
        guard await AVAudioApplication.requestRecordPermission() else {
            errorMessage = "マイクの使用を許可してください（設定 > LatteCoach）"
            return
        }
        await Notifier.requestAuthorization()
        if let client = CoachClient.fromBundle(), let p = try? await client.params() {
            thresholds = FeatureThresholds(serverValues: p.values)
            paramsVersion = p.version
        } else {
            thresholds = FeatureThresholds()
            paramsVersion = nil
        }
        endDetector = SteamEndDetector(thresholds: thresholds)
        calibration = []
        frames = []
        practiceId = UUID()
        segmentSeq = 0
        segmentStartSample = 0
        totalSamples = 0
        framesStartFrame = 0
        frameCounter = 0
        endDetector.reset()
        steamDetected = false
        cupStartedAt = Date()
        do {
            try capture.start()
            try openSegment()
            phase = .calibrating
        } catch {
            errorMessage = "録音を開始できません: \(error.localizedDescription)"
        }
    }

    /// 練習を終える。最後の区間の音をサーバーへ送る（杯にはつかない）
    func stop() {
        capture.stop()
        phase = .idle
        frames = []
        if let tail = closeSegment() {
            Task.detached { await PracticeSession.uploadTail(tail) }
        }
    }

    struct Segment: Sendable {
        let url: URL
        let practiceId: UUID
        let seq: Int
        let sampleRate: Int
    }

    private func openSegment() throws {
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Audio", isDirectory: true)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let url = dir.appendingPathComponent("\(practiceId.uuidString)-\(String(format: "%03d", segmentSeq)).wav")
        segment = try WAVWriter(url: url, sampleRate: Int(capture.audioRate))
        segmentStartSample = totalSamples
    }

    /// 今の区間を閉じて返し、次の区間を始める
    private func closeSegment(reopen: Bool = false) -> Segment? {
        guard let w = segment else { return nil }
        w.close()
        let s = Segment(url: w.url, practiceId: practiceId, seq: segmentSeq, sampleRate: w.sampleRate)
        segment = nil
        segmentSeq += 1
        if reopen { try? openSegment() }
        return s
    }

    private static func uploadTail(_ s: Segment) async {
        guard let client = CoachClient.fromBundle(), let data = try? Data(contentsOf: s.url) else { return }
        if (try? await client.uploadPracticeAudio(practiceId: s.practiceId, seq: s.seq, audio: data)) != nil {
            try? FileManager.default.removeItem(at: s.url)
        }
    }

    /// 今の杯を区切り、特徴量を計算して返す。区間が見つからなければ features は nil。
    func cutCup() -> Cup {
        let features = FeatureExtractor.extract(frames: frames, background: background, thresholds: thresholds)
        var cup = Cup(startedAt: cupStartedAt, endedAt: Date(), features: features)
        cup.paramsVersion = paramsVersion
        let bg = max(background, 1e-12)
        // 有効数字3桁に丸めて送信量を抑える
        func r(_ v: Float) -> Float { v == 0 ? 0 : Float(String(format: "%.3g", v / bg)) ?? v / bg }
        cup.envelope = frames.map { [r($0.low), r($0.mid), r($0.high), r($0.top)] }
        // 判定の境の位置（包絡の先頭からの秒）。サーバーが音の絵を切り出し、縦線を引くのに使う（sound-picture.md）
        if let f = features, let range = FeatureExtractor.longestSteamRange(frames: frames, background: background, thresholds: thresholds) {
            let start = Double(range.lowerBound) * BandAnalyzer.frameDuration
            cup.marks = ["steam_start": start,
                         "squeal_end": start + f.startSquealSec,
                         "transition": start + f.transitionAt * f.steamDurationSec,
                         "steam_end": Double(range.upperBound) * BandAnalyzer.frameDuration]
        }
        // 前回の区切りからの音を全部この杯につけて送る（スチームの切り出しはサーバーで何度でもやり直せる）
        let lastSegmentStart = segmentStartSample
        if let seg = closeSegment(reopen: true) {
            cup.audioPath = seg.url.lastPathComponent
            cup.practiceId = seg.practiceId
            cup.segmentSeq = seg.seq
            // 音の先頭が、包絡（frames）の先頭から何秒後か。最初の杯は背景を測った時間を含むので負になる
            let perFrame = capture.audioRate * BandAnalyzer.frameDuration
            cup.audioStartSec = (Double(lastSegmentStart) - Double(framesStartFrame) * perFrame) / capture.audioRate
            cup.background = background
        }
        frames = []
        framesStartFrame = frameCounter
        endDetector.reset()
        steamDetected = false
        cupStartedAt = Date()
        return cup
    }

    private func consume(_ new: [BandFrame], audio newAudio: [Int16]) {
        if phase != .idle {
            segment?.append(newAudio)
            totalSamples += newAudio.count
            frameCounter += new.count
        }
        switch phase {
        case .idle:
            return
        case .calibrating:
            calibration += new.map(\.total)
            if Double(calibration.count) * BandAnalyzer.frameDuration >= Self.calibrationSec {
                // 中央値を背景音にする（測定中に物音が入っても引きずられにくい）
                background = max(calibration.sorted()[calibration.count / 2], 1e-10)
                phase = .listening
            }
        case .listening:
            if frames.isEmpty { framesStartFrame = frameCounter - new.count }
            frames += new
            // 区切り忘れで際限なく溜まらないよう、包絡は直近 10 分に留める（音はファイルに全部残る）
            if frames.count > 6000 {
                let drop = frames.count - 6000
                frames.removeFirst(drop)
                framesStartFrame += drop
            }
            for f in new where endDetector.feed(f, background: background) {
                steamDetected = true
                Notifier.steamEnded()
            }
            if let last = new.last {
                levelDb = 10 * log10(Double(max(last.total, 1e-12) / background))
            }
        }
    }
}
