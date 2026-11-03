import AVFoundation

/// マイク入力を 0.1 秒ごとの帯域エネルギーに変換して渡す。生の音声はファイルにもネットワークにも出さない。
final class AudioCapture {
    /// 解析スレッドから呼ばれる。UI 更新は呼び出し側でメインへ移すこと
    var onFrames: (([BandFrame]) -> Void)?

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

        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 4096, format: format) { [weak self] buffer, _ in
            guard let self, let channel = buffer.floatChannelData?[0] else { return }
            let samples = Array(UnsafeBufferPointer(start: channel, count: Int(buffer.frameLength)))
            self.queue.async {
                let frames = analyzer.append(samples)
                if !frames.isEmpty { self.onFrames?(frames) }
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
