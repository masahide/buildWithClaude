import AVFoundation
import XCTest
@testable import LatteCoach

final class WAVTests: XCTestCase {
    func testWriterProducesReadableFile() throws {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("\(UUID().uuidString).wav")
        defer { try? FileManager.default.removeItem(at: url) }
        let w = try WAVWriter(url: url, sampleRate: 48_000)
        let tone = (0..<48_000).map { Int16(10_000 * sin(2 * Double.pi * 440 * Double($0) / 48_000)) }
        w.append(Array(tone[..<20_000]))
        w.append(Array(tone[20_000...]))
        w.close()
        let file = try AVAudioFile(forReading: url)
        XCTAssertEqual(file.length, 48_000)
        XCTAssertEqual(file.fileFormat.sampleRate, 48_000)
        XCTAssertEqual(try Data(contentsOf: url).count, 44 + 48_000 * 2)
    }
}
