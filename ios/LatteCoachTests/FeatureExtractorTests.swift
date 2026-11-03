import XCTest
@testable import LatteCoach

/// 合成音で特徴量の向きを確かめる。値そのものではなく「エア入れが長い杯ほど比率が大きい」などの順序を見る。
final class FeatureExtractorTests: XCTestCase {
    func testDetectsSteamAndAirPhase() throws {
        let result = try XCTUnwrap(SyntheticSteam.run(airSec: 8, stirSec: 20, bursts: 0))
        XCTAssertEqual(result.steamDurationSec, 28, accuracy: 1.5)
        XCTAssertEqual(result.airPhaseRatio, 8.0 / 28.0, accuracy: 0.08)
        XCTAssertEqual(result.burstCount, 0)
    }

    func testLongerAirPhaseGivesLargerRatio() throws {
        let short = try XCTUnwrap(SyntheticSteam.run(airSec: 4, stirSec: 20, bursts: 0))
        let long = try XCTUnwrap(SyntheticSteam.run(airSec: 12, stirSec: 20, bursts: 0))
        XCTAssertGreaterThan(long.airPhaseRatio, short.airPhaseRatio + 0.1)
    }

    func testCountsBursts() throws {
        let result = try XCTUnwrap(SyntheticSteam.run(airSec: 6, stirSec: 20, bursts: 5))
        XCTAssertEqual(result.burstCount, 5)
    }

    func testIgnoresShortNoise() {
        // 3 秒のグラインダー相当は弾く
        XCTAssertNil(SyntheticSteam.run(airSec: 3, stirSec: 0, bursts: 0))
    }

    func testSteamEndDetectorFiresOnce() {
        var detector = SteamEndDetector()
        let loud = BandFrame(low: 1, mid: 1, high: 1)
        let quiet = BandFrame(low: 0.01, mid: 0.01, high: 0.01)
        var fired = 0
        for _ in 0..<150 { if detector.feed(loud, background: 0.03) { fired += 1 } }
        for _ in 0..<100 { if detector.feed(quiet, background: 0.03) { fired += 1 } }
        XCTAssertEqual(fired, 1)
    }
}
