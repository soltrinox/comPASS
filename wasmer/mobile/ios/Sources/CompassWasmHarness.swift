import CryptoKit
import Foundation
import UIKit
import WebKit

enum CompassHostError: Error, LocalizedError {
    case missingResource(String)
    case digestMismatch(expected: String, actual: String)
    case jsError(String)

    var errorDescription: String? {
        switch self {
        case let .missingResource(name):
            return "missing bundle resource: \(name)"
        case let .digestMismatch(expected, actual):
            return "digest mismatch expected=\(expected) actual=\(actual)"
        case let .jsError(msg):
            return msg
        }
    }
}

struct CompassParityReport {
    var ok: Bool
    var expectedSha256: String
    var actualSha256: String
    var digestMatch: Bool
    var selectedModelVersionId: String?
    var missingReason: String?
    var error: String?
    var raw: [String: Any]

    static func fromJS(_ obj: [String: Any], nativeActual: String) -> CompassParityReport {
        let fixture = obj["fixture_min"] as? [String: Any]
        let missing = obj["missing"] as? [String: Any]
        return CompassParityReport(
            ok: obj["ok"] as? Bool ?? false,
            expectedSha256: obj["expected_sha256"] as? String ?? "",
            actualSha256: (obj["actual_sha256"] as? String) ?? nativeActual,
            digestMatch: obj["digest_match"] as? Bool ?? false,
            selectedModelVersionId: fixture?["selected_model_version_id"] as? String,
            missingReason: missing?["default_reason"] as? String,
            error: obj["error"] as? String,
            raw: obj
        )
    }
}

/// iOS host: SHA-256 pin from SHA256SUMS, then WKWebView + WebAssembly.instantiate.
final class CompassWasmHarness {
    static let expectedResource = "EXPECTED_SHA256"
    static let wasmResource = "compass_core_bg"
    static let wasmExt = "wasm"

    let bundle: Bundle

    init(bundle: Bundle = .main) {
        self.bundle = bundle
    }

    func expectedDigest() throws -> String {
        guard let url = bundle.url(forResource: Self.expectedResource, withExtension: nil)
                ?? bundle.url(forResource: Self.expectedResource, withExtension: "txt") else {
            throw CompassHostError.missingResource(Self.expectedResource)
        }
        return try String(contentsOf: url, encoding: .utf8)
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
    }

    func wasmData() throws -> Data {
        guard let url = bundle.url(forResource: Self.wasmResource, withExtension: Self.wasmExt) else {
            throw CompassHostError.missingResource("\(Self.wasmResource).\(Self.wasmExt)")
        }
        return try Data(contentsOf: url)
    }

    func sha256Hex(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }

    @discardableResult
    func verifyNativeDigest() throws -> String {
        let expected = try expectedDigest()
        let actual = sha256Hex(try wasmData())
        if actual != expected {
            throw CompassHostError.digestMismatch(expected: expected, actual: actual)
        }
        return actual
    }

    func makeWebView(messageHandler: WKScriptMessageHandler) throws -> WKWebView {
        _ = try verifyNativeDigest()
        let config = WKWebViewConfiguration()
        config.defaultWebpagePreferences.allowsContentJavaScript = true
        config.userContentController.addUserScript(try makeInjectScript())
        config.userContentController.addUserScript(try makeHostScript())
        config.userContentController.add(messageHandler, name: "compassResult")
        let wv = WKWebView(frame: CGRect(x: 0, y: 0, width: 390, height: 844), configuration: config)
        wv.accessibilityIdentifier = "compassWebView"
        if #available(iOS 16.4, *) {
            wv.isInspectable = true
        }
        return wv
    }

    func makeInjectScript() throws -> WKUserScript {
        let wasm = try wasmData()
        let expected = try expectedDigest()
        let actual = sha256Hex(wasm)
        var snapshot = "{}"
        if let url = bundle.url(forResource: "snapshot_min", withExtension: "json") {
            snapshot = try String(contentsOf: url, encoding: .utf8)
        }
        let payload: [String: Any] = [
            "expectedSha256": expected,
            "wasmB64": wasm.base64EncodedString(),
            "snapshotJson": snapshot,
            "nowIso": "2026-09-05T00:00:00Z",
            "nativeDigestMatch": actual == expected,
            "nativeActualSha256": actual,
        ]
        let data = try JSONSerialization.data(withJSONObject: payload)
        guard let json = String(data: data, encoding: .utf8) else {
            throw CompassHostError.jsError("inject JSON utf-8")
        }
        let source = "window.__COMPASS_INJECT = \(json);"
        return WKUserScript(source: source, injectionTime: .atDocumentStart, forMainFrameOnly: true)
    }

    func makeHostScript() throws -> WKUserScript {
        let js = try String(contentsOf: try resourceURL(name: "host", ext: "js"), encoding: .utf8)
        return WKUserScript(source: js, injectionTime: .atDocumentStart, forMainFrameOnly: true)
    }

    func resourceURL(name: String, ext: String) throws -> URL {
        guard let url = bundle.url(forResource: name, withExtension: ext) else {
            throw CompassHostError.missingResource("\(name).\(ext)")
        }
        return url
    }

    func load(into webView: WKWebView) {
        // Injected host.js + wasm bytes; no custom-scheme fetch (WKWebView fetch status 0).
        let html = """
        <!DOCTYPE html><html><head><meta charset="utf-8"></head>
        <body><pre id="out">booting</pre></body></html>
        """
        webView.loadHTMLString(html, baseURL: nil)
    }

    /// Run decide parity inside WKWebView and return the JS report.
    func runParity(timeoutSeconds: TimeInterval = 45) async throws -> CompassParityReport {
        let nativeActual = try verifyNativeDigest()
        let box = MessageBox()
        let wv = try makeWebView(messageHandler: box)
        box.retainWebView = wv
        let window = UIWindow(frame: UIScreen.main.bounds)
        let root = UIViewController()
        root.view.backgroundColor = .white
        wv.frame = root.view.bounds
        wv.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        root.view.addSubview(wv)
        window.rootViewController = root
        window.makeKeyAndVisible()
        box.retainWindow = window
        load(into: wv)
        let raw = try await box.awaitMessage(timeout: timeoutSeconds)
        let report = CompassParityReport.fromJS(raw, nativeActual: nativeActual)
        print("COMPASS_MOBILE_RESULT_BEGIN")
        if let data = try? JSONSerialization.data(withJSONObject: raw, options: [.prettyPrinted]),
           let text = String(data: data, encoding: .utf8) {
            print(text)
        }
        print("COMPASS_MOBILE_RESULT_END")
        print("COMPASS_MOBILE_NATIVE_SHA256=\(nativeActual)")
        CompassResultStore.write(raw)
        return report
    }
}

final class CompassResultStore {
    static let fileName = "compass-parity.json"

    static func write(_ obj: [String: Any]) {
        guard JSONSerialization.isValidJSONObject(obj),
              let data = try? JSONSerialization.data(withJSONObject: obj, options: [.prettyPrinted, .sortedKeys]) else {
            return
        }
        let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        try? data.write(to: dir.appendingPathComponent(fileName), options: .atomic)
    }
}

final class MessageBox: NSObject, WKScriptMessageHandler {
    var retainWebView: WKWebView?
    var retainWindow: UIWindow?
    private var continuation: CheckedContinuation<[String: Any], Error>?
    private var timer: Timer?

    func userContentController(
        _ userContentController: WKUserContentController,
        didReceive message: WKScriptMessage
    ) {
        timer?.invalidate()
        if let dict = message.body as? [String: Any] {
            continuation?.resume(returning: dict)
        } else if let s = message.body as? String,
                  let data = s.data(using: .utf8),
                  let dict = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            continuation?.resume(returning: dict)
        } else {
            continuation?.resume(throwing: CompassHostError.jsError("unexpected message \(message.body)"))
        }
        continuation = nil
    }

    func awaitMessage(timeout: TimeInterval) async throws -> [String: Any] {
        try await withCheckedThrowingContinuation { cont in
            self.continuation = cont
            DispatchQueue.main.async {
                self.timer = Timer.scheduledTimer(withTimeInterval: timeout, repeats: false) { [weak self] _ in
                    self?.continuation?.resume(throwing: CompassHostError.jsError("timeout waiting for compassResult"))
                    self?.continuation = nil
                }
            }
        }
    }
}
