# Mobile packaging

**Status: PARTIAL** (iOS Simulator) — Android **NOT_RUN**. See [`NOT_RUN.md`](NOT_RUN.md) (filename kept; the status field is the grade).

Both hosts load the same `../artifacts/compass_core_bg.wasm` **by digest** (`SHA256SUMS`), feed a sanitized keyless snapshot, and call `compass_decide_json`. Reason codes match Python/`scripts/wasmer_parity.py`: fixture_min → `urn:mg:model:cheap`; missing snapshot → `snapshot_missing`.

| Tree | Role |
|---|---|
| [`shared/host.js`](shared/host.js) | Shared instantiate + decide glue |
| [`ios/`](ios/) | WKWebView host; `./ios/run-simulator.sh` |
| [`android/`](android/) | System WebView host; `./android/run-emulator.sh` |
| [`sync-assets.sh`](sync-assets.sh) | Copy wasm after verifying `SHA256SUMS` |
| [`run-hosts.sh`](run-hosts.sh) | Glue + size budget + iOS + Android (honest skip) |

```bash
./wasmer/mobile/run-hosts.sh
# or: ./scripts/validate-wasmer-mobile.sh
```

Do not treat Node glue success as a device run. Do not claim FULL without a physical-device log.
