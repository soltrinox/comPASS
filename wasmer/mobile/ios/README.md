# iOS WKWebView host

Minimal iOS 17+ app that:

1. Reads `compass_core_bg.wasm` from the app bundle.
2. Verifies SHA-256 against `EXPECTED_SHA256` (copied from `wasmer/artifacts/SHA256SUMS` by `../sync-assets.sh`).
3. Serves the shared `index.html` / `host.js` over a `compasshost://` scheme.
4. Instantiates the module (`WebAssembly.instantiate`, empty import table) and calls `compass_decide_json`.

Parity (same as `scripts/wasmer_parity.py`):

- fixture snapshot → `selected_model_version_id = urn:mg:model:cheap`
- missing snapshot → `default_reason = snapshot_missing`

```bash
# from repo root
./wasmer/mobile/sync-assets.sh
./wasmer/mobile/ios/run-simulator.sh
```

Requires Xcode and an available iPhone simulator. `CODE_SIGNING_ALLOWED=NO` is for simulator only; a physical device needs a development team (not claimed FULL without a device log).

Regenerate the Xcode project after editing `project.yml`:

```bash
cd wasmer/mobile/ios && xcodegen generate
```
