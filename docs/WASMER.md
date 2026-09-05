# Wasmer / WASM deploy runbook (Track D)

**Status (2026-09-05):** Rust `compass-core` crate builds `wasm32-unknown-unknown` (browser) and `wasm32-wasip1` (desktop Wasmer). Artifacts hashed under `wasmer/artifacts/`. Fail-open parity script green vs Python `compass.core`. Mobile device matrix remains **NOT_RUN**.

**Contract:** [`STACK.md`](STACK.md) §3 · **ABI:** [`abi/host-abi.v1.md`](abi/host-abi.v1.md)

## What is in the module

| In WASM (`compass.core` / `compass-core`) | Native sidecar only |
|---|---|
| `classify`, score-from-snapshot, `decide_from_snapshot` | Probe runner / canary |
| Immutable GraphSnapshot parse/read | Catalog fetch, HF/OpenRouter clients |
| Fail-open default table | Proxy that holds provider keys |
| `RouteDecision` JSON | Bundle sync / credentialed writes |

## Artifact names

| Artifact | Target | Notes |
|---|---|---|
| `wasmer/artifacts/compass_core_bg.wasm` | browser sandbox | **BUILT** — 103980 bytes; SHA-256 `9ad58acccd85e361baf9a789cdd82e95cb264dd9ddc9691236200c6ceb2507db` |
| `wasmer/artifacts/compass-decide.wasm` | desktop Wasmer CLI | **BUILT** — 135419 bytes; SHA-256 `e77301bed6f3bcdf8541ba7256cb6a4e58e1da62d7a98edb52fa27bdc1fee553` |
| same `compass_core_bg.wasm` bytes | mobile (when host exists) | **NOT_RUN** on device; module is build-once |
| Python `compass.core` | native CI / fail-open parity | available |

Module size budget (browser cdylib): **~101 KiB** (track regressions in `SHA256SUMS`).

## Host ABI version

- `COMPASS_HOST_ABI = 1.0.0`
- Module: `ABI_MIN=1.0.0` / `ABI_MAX=1.999.0`
- JSON: `docs/abi/host-abi.v1.json`
- Browser exports: `compass_alloc`, `compass_free`, `compass_decide_json`, `compass_last_len`, `memory` (no `fetch` import)

## Pairing Probe sidecar

1. Native Probe writes a **sanitized** snapshot (JSON `model-graph/v1`) to a host path or SHM.
2. Host implements `storage.read_snapshot` → bytes (strip secrets first).
3. Instantiate module (Wasmer / browser) or call `compass.core.decide_from_snapshot` (Python).
4. Sidecar receives decision JSON and performs provider HTTP **outside** WASM.

## Browser CSP notes

- No `eval` of host secrets into the module.
- Do not expose `fetch` import on the browser build (verified: empty import table).
- Fail-open if instantiate/decide throws → configured default + `module_trap`.
- Sandbox page: `wasmer/browser/` (serve `wasmer/` over HTTP).

## Desktop / mobile packaging

- **Desktop:** `wasmer run wasmer/artifacts/compass-decide.wasm --volume …`
- **Mobile:** **NOT_RUN** — no CI device farm; reuse `compass_core_bg.wasm` when a Wasmer-capable mobile host is available.

## Fail-open parity

Same reason codes on native core and WASM:

| Case | `default_reason` |
|---|---|
| Missing snapshot | `snapshot_missing` |
| Truncated/corrupt JSON | `snapshot_corrupt` |
| Decide trap / exception | `module_trap` |
| Empty candidate set | `no_candidates` |
| ABI mismatch | `abi_incompatible` |

Proof: `python scripts/wasmer_parity.py` → `test-results/wasmer-parity/parity.json`.  
Tests: `tests/test_wasmer_parity.py`, `tests/test_wasm_boundary.py`, `tests/test_core_decide.py`.

## CI matrix

| Job | Target | Must pass |
|---|---|---|
| `core-native` | linux + macos Python | unit decide/classify (skip live wasmer) |
| `core-wasm` | wasm32 + Wasmer | build, validate, decide fixture, no fetch import |
| `fail-open-parity` | native vs wasm | identical defaulting |
| `mobile` | placeholder | explicit NOT_RUN |

No live provider keys in CI.

## Rollback

Pin previous module hash from `wasmer/artifacts/SHA256SUMS` in host config. Until hosts pin wasm, also pin the Python package version (`compass-router`).

## What is **not** in the module

Keys, Probe, ingest, proxy-with-keys, unrestricted filesystem, env lookup of `*_API_KEY`.

## Sanitization

No machine-specific absolute paths in module or glue (no `/Users/...` baked into WASI preopens). Hosts supply workspace-relative roots via `--volume`.

## Operator install (Wasmer CLI)

```bash
brew install wasmer   # or: curl https://get.wasmer.io -sSfL | sh
wasmer --version
```
