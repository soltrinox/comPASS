# wasmer/ — Track D packaging surface

## Status

| Target | Status | Notes |
|---|---|---|
| Python `compass.core` (wasm-boundary stand-in) | **READY** | Import-graph + fail-open tests |
| Browser sandbox `.wasm` | **READY** | `artifacts/compass_core_bg.wasm` + `browser/` + headless smoke |
| Desktop Wasmer embed | **READY** | `artifacts/compass-decide.wasm` + `desktop/run-decide.sh` shell |
| Mobile Wasmer | **NOT_RUN** | See `mobile/NOT_RUN.md` — same module bytes when a host exists |

## Artifacts (hashed)

| File | Size | SHA-256 |
|---|---|---|
| `artifacts/compass_core_bg.wasm` | 103980 bytes | `9ad58acccd85e361baf9a789cdd82e95cb264dd9ddc9691236200c6ceb2507db` |
| `artifacts/compass_core.wasm` | (same bytes as bg) | same |
| `artifacts/compass-decide.wasm` | 135419 bytes | `e77301bed6f3bcdf8541ba7256cb6a4e58e1da62d7a98edb52fa27bdc1fee553` |

Full sums: [`artifacts/SHA256SUMS`](artifacts/SHA256SUMS).

```
e77301bed6f3bcdf8541ba7256cb6a4e58e1da62d7a98edb52fa27bdc1fee553  ../artifacts/compass-decide.wasm
9ad58acccd85e361baf9a789cdd82e95cb264dd9ddc9691236200c6ceb2507db  ../artifacts/compass_core.wasm
9ad58acccd85e361baf9a789cdd82e95cb264dd9ddc9691236200c6ceb2507db  ../artifacts/compass_core_bg.wasm
```

Rebuild:

```bash
cd wasmer/crate
cargo build --release --target wasm32-unknown-unknown --lib
cargo build --release --target wasm32-wasip1 --bin compass-decide
cp target/wasm32-unknown-unknown/release/compass_core.wasm ../artifacts/compass_core_bg.wasm
cp target/wasm32-unknown-unknown/release/compass_core.wasm ../artifacts/compass_core.wasm
cp target/wasm32-wasip1/release/compass-decide.wasm ../artifacts/compass-decide.wasm
shasum -a 256 ../artifacts/*.wasm | tee ../artifacts/SHA256SUMS
```

## Layout

```
wasmer/
  README.md
  fixtures/snapshot_min.json
  crate/                 # Rust compass-core (cdylib + WASI bin)
  artifacts/             # hashed .wasm outputs
  browser/               # CSP sandbox page + JS glue + smoke package.json
  desktop/               # packaged Wasmer shell (run-decide.sh, wasmer.toml)
  mobile/                # NOT_RUN ADR + next steps
```

## Run (Python stand-in)

```bash
.venv/bin/python -m pytest tests/test_wasm_boundary.py tests/test_core_decide.py -q
```

## Run (Wasmer desktop)

Requires `wasmer` on PATH (Homebrew: `brew install wasmer`).

```bash
wasmer run wasmer/artifacts/compass-decide.wasm --volume "$PWD/wasmer:/wasmer" -- \
  --request "implement a function" \
  --snapshot /wasmer/fixtures/snapshot_min.json \
  --now "2026-09-05T00:00:00Z"
```

## Fail-open parity

```bash
.venv/bin/python scripts/wasmer_parity.py
# evidence: test-results/wasmer-parity/parity.json
```

Native Python `compass.core.decide_from_snapshot` is the reference for reason codes.
Divergence is a release blocker.

## Browser sandbox

```bash
cd wasmer && python3 -m http.server 8765
# http://127.0.0.1:8765/browser/
```

## Key boundary checklist

```bash
rg -i 'api_key|token|secret|authorization|openrouter|cursor_api' src/compass/core wasmer/crate/src
# expect: no credential handling
wasmer inspect wasmer/artifacts/compass_core_bg.wasm   # Imports: empty
```

## Headless browser smoke (Track J)

```bash
cd wasmer/browser && npm install && npx playwright install chromium
node scripts/wasmer_browser_smoke.mjs   # from repo root; COMPASS_SMOKE_CHANNEL=chrome locally
# evidence: test-results/j-wasmer-packaging/browser-smoke.json
```

## Desktop packaged shell

```bash
./wasmer/desktop/run-decide.sh
COMPASS_FAIL_OPEN_DEMO=corrupt ./wasmer/desktop/run-decide.sh
```

## Size budget

```bash
python scripts/wasmer_size_budget.py
```
