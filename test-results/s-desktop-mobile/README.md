# s-desktop-mobile — stage evidence (plan B3 desktop only)

Stage: **B3 desktop reconcile** (`b3-desktop`).
Captured 2026-09-07 PT (2026-09-08Z) on branch `feat/consolidation-and-wasmer`.

**Mobile is not covered here.** B4 owns Android/iOS hosts. These files are
desktop-only so a later mobile stage can share this directory without this
stage claiming that work.

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

## Re-run

```bash
python scripts/wasmer_desktop_packaged.py
python scripts/wasmer_parity.py
python scripts/wasmer_size_budget.py
python -m pytest tests/test_wasmer_desktop_packaged.py tests/test_wasmer_parity.py tests/test_wasmer_size_budget.py -q
```

## Not covered here

Mobile hosts, registry publish, browser `@wasmer/sdk`, full pytest, and the
cross-cutting proof report. `docs/` WASMER path references are owned by a
parallel consolidation agent.
