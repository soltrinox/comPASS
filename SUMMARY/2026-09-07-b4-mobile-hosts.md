# Session summary — B4 mobile hosts (2026-09-07 PT)

**Branch:** `feat/consolidation-and-wasmer`  
**Scope:** Plan todo `b4-mobile` only. Did not edit the plan file.  
**Grade:** **PARTIAL** (iOS Simulator). Android **NOT_RUN**. Not FULL (no physical-device log).

## Host code

| Path | Role |
|---|---|
| `wasmer/mobile/shared/host.js` | Digest check, empty-import instantiate, `compass_decide_json` |
| `wasmer/mobile/ios/` | WKWebView app + `run-simulator.sh` |
| `wasmer/mobile/android/` | System WebView app + `run-emulator.sh` |
| `scripts/validate-wasmer-mobile.sh` | Discoverable runner |

## Five steps (`NOT_RUN.md`)

1. Host pick: iOS WKWebView + Android WebView (same JS ABI as `sandbox.js`).
2. Trees added; wasm loaded by `SHA256SUMS` digest; keyless snapshot; `compass_decide_json`.
3. CI workflow `.github/workflows/wasmer-mobile.yml` (honest Android skip).
4. Status field flipped to PARTIAL; `docs/WASMER.md` matrix updated. Filename `NOT_RUN.md` retained for CI `test -f`.
5. Size budget green (103980 ≤ 150000); same hash as `SHA256SUMS`.

## Runtime

- **iOS Simulator:** iPhone 16 Pro / iOS 18.6 via `simctl` (Xcode 26.2 had no scheme simulator destinations). fixture_min → `urn:mg:model:cheap`; missing → `snapshot_missing`.
- **Android:** SDK absent — compile/emulator **NOT_RUN**.
- **Node glue:** same reason codes; not a device run.

## Evidence

`test-results/s-desktop-mobile/mobile-ios-simulator.json`, `mobile-android.json`, `mobile-glue-check.json`, `mobile-size-budget.json`. Desktop B3 files left in place.

## Human blockers

- Android SDK + licenses + API 34 emulator/device.
- iOS 26.2 Simulator runtime (for `xcodebuild -destination` tests).
- Development team / signing for a physical device (FULL).
- A connected iPad was ineligible (`iOS 26.2 is not installed` device support).
