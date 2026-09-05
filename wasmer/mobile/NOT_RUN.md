# ADR-quality: Mobile Wasmer device matrix — NOT_RUN

**Status:** NOT_RUN (2026-09-05 PT)  
**Track:** J (Wasmer browser/mobile)  
**Module:** reuse `wasmer/artifacts/compass_core_bg.wasm` (build-once; empty import table)

## Decision

Do **not** claim mobile host coverage in CI. There is no iOS/Android device farm, TestFlight lane, or emulator job wired to this repo. Desktop Wasmer shell (`wasmer/desktop/run-decide.sh`) and headless browser smoke cover packaged run paths for Track J exit.

## Context

- Route+Graph module is `wasm32-unknown-unknown` cdylib suitable for mobile WASM hosts when one exists.
- Probe remains native sidecar (never in WASM).
- App Store submission is an explicit non-goal for Track J.

## Consequences

- Release notes may advertise **browser-tested** + **desktop Wasmer shell** wasm.
- Mobile remains **NOT_RUN** until a host integration lands.

## Exact next steps (when unblocking)

1. Pick host: Wasmer SDK on Android (JNI/Kotlin) **or** iOS `WKWebView` + `WebAssembly.instantiate` (same browser glue as `wasmer/browser/sandbox.js`) **or** third-party mobile Wasmer embed.
2. Add `wasmer/mobile/<android|ios>/` with a minimal host that:
   - loads `compass_core_bg.wasm` from app assets;
   - feeds a sanitized snapshot (no keys);
   - calls `compass_decide_json`;
   - surfaces fail-open reason codes identical to Python/`wasmer_parity.py`.
3. CI: emulator job (Android API 34) **or** macOS runner + iOS Simulator; no provider secrets; upload `test-results/j-wasmer-packaging/mobile-*.log.txt`.
4. Flip this file’s status to PARTIAL (emulator) or FULL (device) and update `docs/WASMER.md` matrix.
5. Size budget: keep browser cdylib under documented threshold; mobile hosts share the same artifact hash from `SHA256SUMS`.

## Alternatives considered

| Option | Why deferred |
|---|---|
| Browser-only on mobile Safari | Useful smoke, not a native packaging path |
| Publish to App Store | Out of scope |
| Fake green CI without device | Forbidden — keep honest NOT_RUN |
