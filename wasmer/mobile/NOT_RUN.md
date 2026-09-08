# ADR-quality: Mobile Wasmer device matrix — PARTIAL (iOS Simulator)

**Status:** PARTIAL (iOS Simulator, 2026-09-07 PT / 2026-09-08Z)  
**Track:** J (Wasmer browser/mobile) + plan B4  
**Module:** reuse `wasmer/artifacts/compass_core_bg.wasm` (build-once; empty import table; SHA-256 `9ad58acccd85e361baf9a789cdd82e95cb264dd9ddc9691236200c6ceb2507db`)

Filename kept as `NOT_RUN.md` so existing CI `test -f wasmer/mobile/NOT_RUN.md` still resolves. The **status field** is the grade.

## Decision

Do **not** claim FULL (physical device) or Android emulator coverage. iOS Simulator ran the shared host glue against the pinned cdylib and matched Python reason codes. Android host sources exist; the SDK/emulator were not present, so Android remains **NOT_RUN**. Fake green CI is still forbidden.

## What landed (five steps)

1. **Host pick:** iOS `WKWebView` + `WebAssembly.instantiate` (same ABI as `wasmer/browser/sandbox.js`). Android System WebView host tree for the same JS glue (`wasmer/mobile/shared/host.js`). No JNI Wasmer SDK (not a maintained Android product path here).
2. **Trees:** `wasmer/mobile/ios/` and `wasmer/mobile/android/`. Both load `compass_core_bg.wasm` **by digest** from `SHA256SUMS`, sanitize a keyless snapshot, call `compass_decide_json`.
3. **CI:** `.github/workflows/wasmer-mobile.yml` — Node glue check + size budget on Ubuntu; iOS Simulator job on macOS; Android runner exits 2 with NOT_RUN unless an SDK/device is provisioned. Logs upload from `test-results/s-desktop-mobile/`.
4. **Grade:** **PARTIAL** (iOS Simulator evidence). **FULL** still requires a physical device log. Android **NOT_RUN** (no SDK).
5. **Size budget:** browser cdylib 103980 bytes (≤150000). Mobile hosts share the same `SHA256SUMS` hash.

## Parity observed (iOS Simulator)

| Case | Result | Evidence |
|---|---|---|
| fixture_min | `urn:mg:model:cheap` | `test-results/s-desktop-mobile/mobile-ios-simulator.json` |
| missing snapshot | `snapshot_missing` | same |
| digest | matches `SHA256SUMS` (`compass_core_bg.wasm`) | CryptoKit pin + report `actual_sha256` |

Shared JS glue also passes in Node (not a device run): `mobile-glue-check.json`.

## Human follow-up (blockers for FULL / Android PARTIAL)

- Install Android SDK (API 34), accept licenses, run `./wasmer/mobile/android/run-emulator.sh`.
- For `xcodebuild test` destinations under Xcode 26.2: install the **iOS 26.2 Simulator runtime** (Components). This machine used `simctl` install/launch because scheme destinations did not list simulators.
- Physical device: development team / signing; do not claim FULL without that log.
- Connected iPad was visible to xcodebuild but ineligible (`iOS 26.2 is not installed` device support).

## Context

- Route+Graph module is `wasm32-unknown-unknown` cdylib.
- Probe remains native sidecar (never in WASM).
- App Store submission remains a non-goal.

## Exact next steps (remaining)

1. Provision Android SDK + API 34 emulator or a device; run `connectedDebugAndroidTest`.
2. Optional: install iOS 26.2 simulator runtime so `xcodebuild -destination` test works without the simctl fallback.
3. Device signing + a device log → flip this file to **FULL**.
4. Keep `docs/WASMER.md` matrix in sync with the status field here.

## Alternatives considered

| Option | Why deferred |
|---|---|
| Browser-only on mobile Safari | Useful smoke, not a native packaging path |
| Publish to App Store | Out of scope |
| Fake green CI without device/emulator | Forbidden |
| Wasmer JNI on Android | No maintained Android JNI SDK in-tree; WebView instantiate matches the iOS ABI |
