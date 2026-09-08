import SwiftUI
import WebKit

struct ContentView: View {
    @State private var status = "verifying digest…"

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("comPASS mobile host")
                .font(.headline)
            Text(status)
                .font(.caption)
                .accessibilityIdentifier("compassStatus")
            CompassWebView(status: $status)
        }
        .padding()
    }
}

struct CompassWebView: UIViewRepresentable {
    @Binding var status: String

    func makeCoordinator() -> Coordinator {
        Coordinator(status: $status)
    }

    func makeUIView(context: Context) -> WKWebView {
        context.coordinator.makeWebView()
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    final class Coordinator: NSObject, WKScriptMessageHandler {
        var status: Binding<String>
        var harness: CompassWasmHarness?
        var webView: WKWebView?

        init(status: Binding<String>) {
            self.status = status
        }

        func makeWebView() -> WKWebView {
            let harness = CompassWasmHarness()
            self.harness = harness
            do {
                try harness.verifyNativeDigest()
                let wv = try harness.makeWebView(messageHandler: self)
                self.webView = wv
                harness.load(into: wv)
                status.wrappedValue = "module loading"
                return wv
            } catch {
                status.wrappedValue = "digest/load failed: \(error)"
                return WKWebView()
            }
        }

        func userContentController(
            _ userContentController: WKUserContentController,
            didReceive message: WKScriptMessage
        ) {
            if let body = message.body as? [String: Any],
               let ok = body["ok"] as? Bool {
                let selected = (body["fixture_min"] as? [String: Any])?["selected_model_version_id"] as? String ?? "?"
                let missing = (body["missing"] as? [String: Any])?["default_reason"] as? String ?? "?"
                status.wrappedValue = ok
                    ? "ok fixture=\(selected) missing=\(missing)"
                    : "fail \(body["error"] ?? "unknown")"
            } else {
                status.wrappedValue = String(describing: message.body)
            }
            if let body = message.body as? [String: Any] {
                CompassResultStore.write(body)
            }
        }
    }
}
