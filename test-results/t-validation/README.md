# t-validation — cross-cutting proof capture

**Date:** 2026-09-07 PT (`TS=20260907-212310`)
**Branch:** `feat/consolidation-and-wasmer` @ `305609a` (plus this commit)
**Scope:** plan todo `validation` only. No feature re-implementation.

**Proof report (read this):** [`../PROOF-consolidation-wasmer-20260907.md`](../PROOF-consolidation-wasmer-20260907.md)

Raw `.log.txt` transcripts are gitignored (`.gitignore` line 15). The committed `.txt` / `.json` files below quote the same runs.

## This-run artifacts

| File | What |
|---|---|
| `pytest-schema.txt` | `tests/test_schema.py` — 10 passed |
| `pytest-full.txt` | default `.venv` full suite — **185 passed** |
| `pytest-paid-sync-default.txt` | 5 passed (local fallback; compressor not importable) |
| `pytest-paid-sync-compressor-venv.txt` | sibling engine FAIL — `AttributeError: lineage` — **NOT_FIXED** |
| `pytest-credential-boundary.txt` | 12 passed — CURSOR_API_KEY stays Probe-only |
| `sync-schema-check.txt` | three schema copies, one digest |
| `wasmer-size-budget.txt` | 103980 ≤ 150000; SHA256SUMS match |
| `wasmer-parity.txt` | Python vs wasm, including fail-open |
| `desktop-smoke.txt` | `run-decide.sh` local `.webc` → `urn:mg:model:cheap` |
| `desktop-fail-open.txt` | `COMPASS_FAIL_OPEN_DEMO=missing` → `snapshot_missing` |
| `wasmer-whoami.txt` | still not logged in |
| `evidence.json` | machine-readable grades |

Playwright browser smoke and iOS Simulator were **not** re-run here. Cite [`../r-browser-sdk/`](../r-browser-sdk/README.md) and [`../s-desktop-mobile/`](../s-desktop-mobile/README.md).
