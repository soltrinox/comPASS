# s-desktop-mobile — stage evidence (B3 desktop + B4 mobile)

Captured on branch `feat/consolidation-and-wasmer`.

Desktop files (`desktop-*.log.txt`, `desktop-evidence.json`) are **B3** and must not be deleted. Mobile files below are **B4**.

## B4 mobile hosts (2026-09-07 PT / 2026-09-08Z)

| Path | Grade | Notes |
|---|---|---|
| iOS WKWebView Simulator | **PARTIAL** | `simctl` install/launch on iPhone 16 Pro (iOS 18.6). fixture_min → `urn:mg:model:cheap`; missing → `snapshot_missing`; digest matches `SHA256SUMS`. Not a physical device (**not FULL**). |
| Android WebView | **NOT_RUN** | Host sources present. No Android SDK (`ANDROID_HOME` unset). Not faked. |
| Shared JS glue (Node) | glue-only | Same `host.js`; **not** a mobile run. |
| Size budget | FULL | `compass_core_bg.wasm` 103980 ≤ 150000; hash unchanged |

### Mobile artifacts

| File | Contents |
|---|---|
| `mobile-ios-simulator.json` | Simulator grade + JS report |
| `mobile-ios-simulator-*.log.txt` | xcodebuild + simctl transcript (gitignored `*.log.txt`) |
| `mobile-android.json` | Honest SDK-missing NOT_RUN |
| `mobile-glue-check.json` | Node instantiate + parity |
| `mobile-size-budget.json` | cdylib size + digest |
| `mobile-hosts-summary.json` | Overall PARTIAL |

### Re-run mobile

```bash
./scripts/validate-wasmer-mobile.sh
# pieces:
node scripts/wasmer_mobile_glue_check.mjs
python scripts/wasmer_size_budget.py
./wasmer/mobile/ios/run-simulator.sh
./wasmer/mobile/android/run-emulator.sh
```

Xcode 26.2 on this machine had no `xcodebuild -destination` simulator entries (iOS 26.2 runtime/component missing). The runner builds `-sdk iphonesimulator` and uses `simctl`. Install the iOS 26.2 Simulator runtime for scheme-based `xcodebuild test`.

## B3 desktop reconcile (unchanged)

Stage: **B3 desktop reconcile** (`b3-desktop`).
Captured 2026-09-07 PT (2026-09-08Z) on branch `feat/consolidation-and-wasmer`.

## Outcome

| Path | Grade | Notes |
|---|---|---|
| Local `.webc` (`wasmer run compass-decide-0.1.0.webc`) | FULL | Default hop. Envelope IDENTICAL to loose wasm |
| Air-gap wasm (`wasmer/artifacts/compass-decide.wasm`) | FULL | Same volume map as `scripts/wasmer_parity.py` |
| Registry-by-name (`wasmer run compass/decide@0.1.0`) | **PARTIAL** | Code present in `run-decide.sh`. Runtime **NOT_RUN** — no login, namespace `compass` unclaimed. Not faked. |
| Module trust root vs B1 | FULL | Unpacked `compass-decide` / `compass-core` bytes MATCH `SHA256SUMS`. Outer `.webc` wrapper digest may differ from `PACKAGE-DIGESTS.json` without a module change. |

## Run order (`wasmer/desktop/run-decide.sh`)

1. If `COMPASS_WASMER_USE_REGISTRY=1` or `--registry`, try `wasmer run <name>@<version>`. On failure, log honestly and fall through.
2. Else (default today): `wasmer run --offline` the local `.webc` (build with `wasmer package build` if missing).
3. Air-gap: `wasmer run --offline wasmer/artifacts/compass-decide.wasm` with `--volume "$PWD/wasmer:/wasmer"`.

`scripts/wasmer_parity.py` still shells `wasmer run` on the raw wasm itself (Python vs wasm). Packaged-vs-loose is `scripts/wasmer_desktop_packaged.py`.

## Artifacts

| File | Contents |
|---|---|
| `desktop-evidence.json` | Machine-readable envelopes, compare errors, registry grade |
| `desktop-packaged-vs-loose.txt` | fixture_min + fail_open_missing, both IDENTICAL |
| `desktop-registry.txt` | Honest registry failure + fallthrough-to-webc |
| `desktop-guards.txt` | size-budget, Python-vs-wasm parity, targeted pytest |
| `desktop-*-<ts>.log.txt` | Same transcripts, gitignored by `test-results/**/*.log.txt` |

## Claim → evidence map

| Claim | Where |
|---|---|
| Packaged webc envelope equals loose wasm (fixture) | `desktop-packaged-vs-loose.txt`, `identical_parsed: true` |
| Reason code `snapshot_missing` matches on both hops | `desktop-packaged-vs-loose.txt`, `fail_open_missing` |
| Registry hop fails with "not found" / NOT_RUN | `desktop-registry.txt` |
| Registry then falls through to webc and still decides | `desktop-evidence.json` `registry_fallthrough` |
| `wasmer_parity.py` / `wasmer_size_budget.py` still green | `desktop-guards.txt` |
| iOS Simulator decide parity | `mobile-ios-simulator.json` |
| Android emulator | `mobile-android.json` (NOT_RUN) |

## Re-run desktop

```bash
python scripts/wasmer_desktop_packaged.py
python scripts/wasmer_parity.py
python scripts/wasmer_size_budget.py
python -m pytest tests/test_wasmer_desktop_packaged.py tests/test_wasmer_parity.py tests/test_wasmer_size_budget.py -q
```

## Not covered here

Registry publish, browser `@wasmer/sdk` (B2), full pytest, and the cross-cutting proof report.
