# Wasmer / WASM deploy runbook (Track D + J)

**Status (2026-09-05 PT):** Rust `compass-core` crate builds `wasm32-unknown-unknown` (browser) and `wasm32-wasip1` (desktop Wasmer). Artifacts hashed under `wasmer/artifacts/`. Fail-open parity script green vs Python `compass.core`. **Headless browser smoke** + **desktop packaged shell** added in Track J. Mobile device matrix remains **NOT_RUN** (ADR: `wasmer/mobile/NOT_RUN.md`).

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

Module size budget (browser cdylib): **≤ 150000 bytes** (~146 KiB). Guard: `python scripts/wasmer_size_budget.py` (also CI). Track regressions in `SHA256SUMS`.

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
- Chrome requires `script-src 'self' 'wasm-unsafe-eval'` for `WebAssembly.instantiate` (set in `wasmer/browser/index.html`).
- Fail-open if instantiate/decide throws → configured default + `module_trap`.
- Sandbox page: `wasmer/browser/` (serve `wasmer/` over HTTP).
- Headless hooks: `window.__COMPASS_SMOKE__`, `?smoke=1`, `data-smoke-ready`.

## Browser CI / headless smoke (Track J)

```bash
# Install deps once (wasmer/browser/package.json)
cd wasmer/browser && npm install && npx playwright install chromium
# From repo root:
node scripts/wasmer_browser_smoke.mjs
# Local with system Chrome:
COMPASS_SMOKE_CHANNEL=chrome node scripts/wasmer_browser_smoke.mjs
```

Workflow: `.github/workflows/wasmer-browser.yml` (no provider keys; uploads `test-results/j-wasmer-packaging/browser-smoke.*`).

## Desktop / mobile packaging

- **Desktop (FULL packaging path):** `./wasmer/desktop/run-decide.sh` — volume map, defaults, fail-open demos; see `wasmer/desktop/README.md` + `wasmer.toml`.
- **Mobile:** **NOT_RUN** — no CI device farm. Exact next steps: [`wasmer/mobile/NOT_RUN.md`](../wasmer/mobile/NOT_RUN.md). Reuse `compass_core_bg.wasm` when a Wasmer-capable mobile host exists.

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
Browser path must match the same defaults on corrupt/missing snapshot (smoke asserts `snapshot_missing` / `snapshot_corrupt`).

## Graded matrix (Track J)

| Target | Grade | Evidence |
|---|---|---|
| Browser headless smoke | FULL when smoke green | `test-results/j-wasmer-packaging/browser-smoke.json` |
| Desktop Wasmer shell | FULL when script + parity green | `wasmer/desktop/run-decide.sh` |
| Artifact size / SHA256 | FULL when budget script green | `test-results/j-wasmer-packaging/size-budget.json` |
| Mobile device farm | NOT_RUN | `wasmer/mobile/NOT_RUN.md` |

## CI matrix

| Job | Target | Must pass |
|---|---|---|
| `core-native` | linux + macos Python | unit decide/classify (skip live wasmer) |
| `core-wasm` | wasm32 + Wasmer | build, validate, decide fixture, no fetch import, size budget, desktop shell |
| `fail-open-parity` | native vs wasm | identical defaulting |
| `browser-smoke` | Playwright chromium | headless sandbox decide + fail-open (`wasmer-browser.yml`) |
| `size-budget` | committed artifacts | SHA256SUMS + ≤150000 browser bytes |
| `mobile` | placeholder | explicit NOT_RUN docs present |

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
