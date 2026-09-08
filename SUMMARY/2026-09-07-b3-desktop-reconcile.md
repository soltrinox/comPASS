# Session summary — B3 desktop reconcile (2026-09-07 PT)

**Branch:** `feat/consolidation-and-wasmer`
**Scope:** Plan todo `b3-desktop` only. Did not edit the plan file.
**Evidence:** [`test-results/s-desktop-mobile/`](../test-results/s-desktop-mobile/README.md) (desktop-only files; no mobile coverage)

## What changed

`wasmer/desktop/run-decide.sh` now runs in this order:

1. **Registry-by-name** — only if `COMPASS_WASMER_USE_REGISTRY=1` or `--registry`. Tries `wasmer run compass/decide@0.1.0`, logs an honest failure, falls through.
2. **Local `.webc` (default)** — `wasmer run --offline compass-decide-0.1.0.webc`, building with `wasmer package build` if missing.
3. **Air-gap wasm** — `wasmer/artifacts/compass-decide.wasm` with `--volume "$PWD/wasmer:/wasmer"`.

`scripts/wasmer_parity.py` still shells `wasmer run` on the loose artifact (Python vs wasm). Packaged-vs-loose is `scripts/wasmer_desktop_packaged.py` / `tests/test_wasmer_desktop_packaged.py`.

## Results

| Check | Result |
|---|---|
| Packaged vs loose envelopes (`fixture_min`, `snapshot_missing`) | IDENTICAL |
| Registry-by-name | PARTIAL — code complete, runtime NOT_RUN, not faked |
| Registry then fall through to webc | envelope still selects `urn:mg:model:cheap` |
| `scripts/wasmer_parity.py` | green |
| `scripts/wasmer_size_budget.py` | green |
| Targeted pytest (3 modules, 4 tests) | 4 passed |

## Left for later

- **B4 mobile** — `wasmer/mobile/NOT_RUN.md`; this stage wrote desktop-only files under `test-results/s-desktop-mobile/` on purpose.
- Human `wasmer login` + claim namespace `compass` + `wasmer publish .` before the registry hop can be graded FULL.
- Stale `wasmer.toml` path references in `docs/WASMER.md` and `docs/WASMER-DEPLOYMENT.md` — owned by the docs consolidation agent.
- Full pytest and the cross-cutting proof report — out of scope for B3.
