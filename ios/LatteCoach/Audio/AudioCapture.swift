import AVFoundation

/// マイク入力を 0.1 秒ごとの帯域エネルギーに変換して渡す。あわせて、同じサンプルレートの 16 bit の音も渡す。
/// 間引かないのは、サーバーで当て直す判定がアプリと同じ結果になるようにするため（間引くと帯域エネルギーが変わり、判定がずれた）。
/// 音はメモリに置くだけで、練習の音を開始から終了まで全部、自宅のサーバーに送る（decisions.md D21）。
final class AudioCapture {
    /// 解析スレッドから呼ばれる。UI 更新は呼び出し側でメインへ移すこと。2つ目は前回からの間引いた音
    var onFrames: (([BandFrame], [Int16]) -> Void)?
    /// 音のサンプルレート（マイクと同じ。ふつう 48 kHz）
    private(set) var audioRate: Double = 48_000
    private var decimate = 1
    private var pendingAudio: [Int16] = []

    private let engine = AVAudioEngine()
    private let queue = DispatchQueue(label: "audio.analysis")
    private var analyzer: BandAnalyzer?

    func start() throws {
        let session = AVAudioSession.sharedInstance()
        // .measurement で自動ゲイン調整などの加工を切る（相対値の特徴量を安定させるため）
        try session.setCategory(.record, mode: .measurement, options: [])
        try session.setActive(true)

        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        let analyzer = BandAnalyzer(sampleRate: format.sampleRate)
        self.analyzer = analyzer
        decimate = 1
        audioRate = format.sampleRate
        pendingAudio = []
        let k = decimate

        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 4096, format: format) { [weak self] buffer, _ in
            guard let self, let channel = buffer.floatChannelData?[0] else { return }
            let samples = Array(UnsafeBufferPointer(start: channel, count: Int(buffer.frameLength)))
            self.queue.async {
                var i = 0
                while i + k <= samples.count {
                    var acc: Float = 0
                    for j in 0..<k { acc += samples[i + j] }
                    self.pendingAudio.append(Int16(max(-1, min(1, acc / Float(k))) * 32767))
                    i += k
                }
                let frames = analyzer.append(samples)
                if !frames.isEmpty {
                    let audio = self.pendingAudio
                    self.pendingAudio = []
                    self.onFrames?(frames, audio)
                }
            }
        }
        engine.prepare()
        try engine.start()
    }

    func stop() {
        engine.inputNode.removeTap(onBus: 0)
        engine.stop()
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    /// 電話などで中断されたあとに再開する
    func resumeAfterInterruption() {
        guard !engine.isRunning else { return }
        try? AVAudioSession.sharedInstance().setActive(true)
        try? engine.start()
    }
}
