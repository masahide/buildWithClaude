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
        XCTAssertEqual(result.firstAirSec, 13, accuracy: 2)
        XCTAssertEqual(result.reAirCount, 0)
        XCTAssertEqual(result.burstCount, 0)
    }

    func testDetectsAddedAirIntake() throws {
        // 11-05 の録音と同じ形: 泡入れ 7 秒 → 渦 4 秒 → 追加の泡入れ 4 秒 → 渦
        let result = try XCTUnwrap(SyntheticSteam.run(airSec: 7, stirSec: 30, bursts: 3, reAirSec: 4))
        XCTAssertEqual(result.firstAirSec, 7, accuracy: 1.5)
        XCTAssertEqual(result.reAirCount, 1)
        XCTAssertEqual(result.reAirSec, 4, accuracy: 1.5)
        // 渦への境は、追加の泡入れの終わり（キュルルル 4 + 泡入れ 7 + 渦 4 + 追加 4 = 19 秒）
        XCTAssertEqual(result.transitionAt * result.steamDurationSec, 19, accuracy: 1.5)
        XCTAssertEqual(result.burstCount, 3)
    }

    func testPurgeIsNotSteam() throws {
        // 空だし（1 秒）は区間に含めない。区間は空だしの後に始まる
        let result = try XCTUnwrap(SyntheticSteam.run(squealSec: 4, airSec: 13, stirSec: 30, bursts: 0))
        XCTAssertLessThan(result.steamDurationSec, 52)
        XCTAssertNil(SyntheticSteam.run(airSec: 0, stirSec: 0, bursts: 0, purgeOnly: true))
    }

    func testFinalPurgeIsNotSteam() throws {
        // 止めてから拭いて、最後に空だし。区間に含めず、終了通知も1回だけ
        let f = SyntheticSteam.frames(squealSec: 4, airSec: 13, stirSec: 30, bursts: 0, finalPurge: true)
        let bg = SyntheticSteam.background(f)
        let result = try XCTUnwrap(FeatureExtractor.extract(frames: f, background: bg))
        XCTAssertEqual(result.steamDurationSec, 49, accuracy: 2)
        var detector = SteamEndDetector()
        XCTAssertEqual(f.filter { detector.feed($0, background: bg) }.count, 1)
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
