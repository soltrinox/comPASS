import XCTest
@testable import CompassMobileHost

final class CompassMobileHostTests: XCTestCase {
    @MainActor
    func testWasmDigestMatchesSHA256SUMSPin() throws {
        let harness = CompassWasmHarness()
        let actual = try harness.verifyNativeDigest()
        XCTAssertEqual(actual.count, 64)
        XCTAssertEqual(actual, try harness.expectedDigest())
    }

    @MainActor
    func testDecideParityFixtureMinAndMissingSnapshot() async throws {
        let harness = CompassWasmHarness()
        let report = try await harness.runParity(timeoutSeconds: 60)
        XCTAssertTrue(report.digestMatch || report.actualSha256 == (try harness.expectedDigest()),
                      "digest must match SHA256SUMS pin")
        XCTAssertEqual(report.selectedModelVersionId, "urn:mg:model:cheap",
                       "fixture_min must match scripts/wasmer_parity.py")
        XCTAssertEqual(report.missingReason, "snapshot_missing",
                       "missing snapshot must match Python fail-open")
        XCTAssertTrue(report.ok, report.error ?? "parity report ok=false")
    }
}
