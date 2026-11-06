// ボイスメモにアプリと同じ判定を当て、3帯域の包絡・背景音・判定の境・特徴量を JSON で出す（開発用）。
// アプリの判定をそのまま使うため、FeatureExtractor.swift と一緒にコンパイルする:
//   swiftc -O ios/LatteCoach/Audio/FeatureExtractor.swift scripts/voice_memo/judge/main.swift -o <出力先>/judge
//   <出力先>/judge 録音.m4a > 録音.json
// 背景音はアプリと同じく、先頭3秒の中央値。音声そのものは出力しない。
import AVFoundation
import Foundation

let url = URL(fileURLWithPath: CommandLine.arguments[1])
let file = try AVAudioFile(forReading: url)
let buf = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: AVAudioFrameCount(file.length))!
try file.read(into: buf)
let samples = Array(UnsafeBufferPointer(start: buf.floatChannelData![0], count: Int(buf.frameLength)))

let analyzer = BandAnalyzer(sampleRate: file.processingFormat.sampleRate)
var frames: [BandFrame] = []
var i = 0
while i < samples.count {  // アプリと同じく 4096 サンプルずつ渡す
    frames += analyzer.append(Array(samples[i..<min(i + 4096, samples.count)]))
    i += 4096
}
let head = frames.prefix(30).map(\.total).sorted()
let bg = max(head[head.count / 2], 1e-12)

let fps = Double(FeatureExtractor.framesPerSecond)
var marks: [String: Double] = [:]
var features: CupFeatures?
if let r = FeatureExtractor.longestSteamRange(frames: frames, background: bg, thresholds: .init()),
   let f = FeatureExtractor.extract(frames: frames, background: bg) {
    features = f
    let start = Double(r.lowerBound) / fps
    marks = ["steam_start": start,
             "transition": start + f.transitionAt * f.steamDurationSec,
             "steam_end": Double(r.upperBound) / fps]
}

func sig3(_ v: Float) -> Float { v == 0 ? 0 : Float(String(format: "%.3g", v)) ?? v }
struct Out: Encodable {
    let frame_sec: Double
    let background: Float
    let bands: [String]
    let envelope: [[Float]]  // 背景音比（線形）、0.1 秒ごとの [低, 中, 高]
    let marks: [String: Double]
    let features: CupFeatures?
}
let out = Out(frame_sec: BandAnalyzer.frameDuration, background: bg,
              bands: ["low 50-400Hz", "mid 400-2000Hz", "high 2000-8000Hz"],
              envelope: frames.map { [sig3($0.low / bg), sig3($0.mid / bg), sig3($0.high / bg)] },
              marks: marks, features: features)
let enc = JSONEncoder()
enc.outputFormatting = [.sortedKeys]
FileHandle.standardOutput.write(try enc.encode(out))
