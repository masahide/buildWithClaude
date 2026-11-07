import Foundation

/// 16 bit モノラルの WAV を作る
enum WAV {
    static func encode(_ samples: [Int16], sampleRate: Int) -> Data {
        var d = Data()
        func u32(_ v: UInt32) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
        func u16(_ v: UInt16) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
        let dataBytes = UInt32(samples.count * 2)
        d.append(contentsOf: Array("RIFF".utf8)); u32(36 + dataBytes); d.append(contentsOf: Array("WAVE".utf8))
        d.append(contentsOf: Array("fmt ".utf8)); u32(16); u16(1); u16(1)
        u32(UInt32(sampleRate)); u32(UInt32(sampleRate * 2)); u16(2); u16(16)
        d.append(contentsOf: Array("data".utf8)); u32(dataBytes)
        samples.withUnsafeBufferPointer { p in
            for s in p { withUnsafeBytes(of: s.littleEndian) { d.append(contentsOf: $0) } }
        }
        return d
    }
}

/// 16 bit モノラルの音を、メモリに溜めずにファイルへ書き続ける。閉じるときにヘッダーの長さを書き込む
final class WAVWriter {
    let url: URL
    let sampleRate: Int
    private let handle: FileHandle
    private(set) var sampleCount = 0

    init(url: URL, sampleRate: Int) throws {
        self.url = url
        self.sampleRate = sampleRate
        FileManager.default.createFile(atPath: url.path, contents: WAV.encode([], sampleRate: sampleRate))
        handle = try FileHandle(forWritingTo: url)
        try handle.seekToEnd()
    }

    func append(_ samples: [Int16]) {
        guard !samples.isEmpty else { return }
        samples.withUnsafeBufferPointer { p in handle.write(Data(buffer: p)) }  // iOS は little endian
        sampleCount += samples.count
    }

    /// ヘッダーの長さを直して閉じる
    func close() {
        let bytes = UInt32(sampleCount * 2)
        func u32(_ v: UInt32) -> Data { withUnsafeBytes(of: v.littleEndian) { Data($0) } }
        try? handle.seek(toOffset: 4); handle.write(u32(36 + bytes))
        try? handle.seek(toOffset: 40); handle.write(u32(bytes))
        try? handle.close()
    }
}
