import XCTest
@testable import LatteCoach

/// 合成音で特徴量の向きを確かめる。値そのものより「泡入れが長い杯ほど比率が大きい」などの順序を見る。
/// 実際の録音での値は log/2026-11-05 を参照
final class FeatureExtractorTests: XCTestCase {
    func testDetectsSteamAndPhases() throws {
        // キュルルル 4 秒 + 泡入れ 13 秒 + 渦 30 秒 + 終わりのキュルキュル 2 秒 = 49 秒
        let result = try XCTUnwrap(SyntheticSteam.run(squealSec: 4, airSec: 13, stirSec: 30, bursts: 0))
        XCTAssertEqual(result.steamDurationSec, 49, accuracy: 2)
        XCTAssertEqual(result.startSquealSec, 4, accuracy: 1)
        XCTAssertEqual(result.airPhaseRatio, 13.0 / 49.0, accuracy: 0.08)
        XCTAssertEqual(result.burstCount, 0)
    }

    func testPurgeIsNotSteam() throws {
        // 空だし（1 秒）は区間に含めない。区間は空だしの後に始まる
        let result = try XCTUnwrap(SyntheticSteam.run(squealSec: 4, airSec: 13, stirSec: 30, bursts: 0))
        XCTAssertLessThan(result.steamDurationSec, 52)
        XCTAssertNil(SyntheticSteam.run(airSec: 0, stirSec: 0, bursts: 0, purgeOnly: true))
    }

    func testLongerAirPhaseGivesLargerRatio() throws {
        let short = try XCTUnwrap(SyntheticSteam.run(airSec: 6, stirSec: 30, bursts: 0))
        let long = try XCTUnwrap(SyntheticSteam.run(airSec: 18, stirSec: 30, bursts: 0))
        XCTAssertGreaterThan(long.airPhaseRatio, short.airPhaseRatio + 0.1)
    }

    func testCountsBursts() throws {
        let result = try XCTUnwrap(SyntheticSteam.run(airSec: 13, stirSec: 30, bursts: 5))
        XCTAssertEqual(result.burstCount, 5)
    }

    func testSteamEndDetectorFiresOnceAfterSteam() {
        let frames = SyntheticSteam.frames(squealSec: 4, airSec: 13, stirSec: 30, bursts: 0)
        let bg = SyntheticSteam.background(frames)
        var detector = SteamEndDetector()
        var firedAt: [Int] = []
        for (i, f) in frames.enumerated() where detector.feed(f, background: bg) { firedAt.append(i) }
        XCTAssertEqual(firedAt.count, 1)
        // スチームが止まる（3 + 1 + 5 + 49 = 58 秒）より後、静かになって数秒以内
        if let at = firedAt.first {
            XCTAssertEqual(Double(at) / 10, 60, accuracy: 2.5)
        }
    }
}
