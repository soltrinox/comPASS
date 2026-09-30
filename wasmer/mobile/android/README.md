# Android WebView host

Minimal API-34-targeted app that:

1. Reads `compass_core_bg.wasm` from APK assets.
2. Verifies SHA-256 against `EXPECTED_SHA256` (from `wasmer/artifacts/SHA256SUMS`).
3. Loads shared `index.html` / `host.js` via `WebViewAssetLoader`.
4. Instantiates the module and calls `compass_decide_json`.

```bash
# Requires Android SDK + licenses + an API 34 emulator or a device.
export ANDROID_HOME=...   # do not commit this path
./wasmer/mobile/android/run-emulator.sh
```

Without an SDK this tree still exists; `run-emulator.sh` exits 2 and writes an honest **NOT_RUN** log. Do not treat assemble-only as PARTIAL.
