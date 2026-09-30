# comPASS consolidation + Wasmer — log-backed proof report

**Purpose:** Cross-cutting Validation stage for the consolidation and Wasmer deployment plan (todo `validation` only).
**Report date:** 2026-09-07 PT (capture `TS=20260907-212310`, UTC 2026-09-08T04:23:10Z)
**Branch:** `feat/consolidation-and-wasmer` (HEAD at capture: `305609a`)
**Plan alignment:** consolidation + Wasmer plan — Parts A and B implementation todos already complete; this report grades them from artifacts and re-runs the required guards.
**Playwright re-run this session:** no
**iOS Simulator re-run this session:** no

`.gitignore` line 15 excludes `test-results/**/*.log.txt`. Claims below quote the committed twins under [`t-validation/`](t-validation/README.md).

## State (validation node)

| Field | Value |
|---|---|
| Node | Critic (Validate + Prove) |
| Implementation | not in scope — no feature work |
| `iteration_count` | 1 |
| `convergence_status` | **CONVERGED** for the offline/local path |
| Registry publish | NOT_RUN (no `wasmer login`; namespace `compass` unclaimed) |
| Android | NOT_RUN (no SDK) |
| Fixes this session | none |

## What was run this session

| Run | Command | Log / twin | Exit |
|---|---|---|---|
| Schema tests | `python -m pytest tests/test_schema.py -v` | [pytest-schema.txt](t-validation/pytest-schema.txt) | 0 |
| Schema mirrors | `python scripts/sync_schema.py --check` | [sync-schema-check.txt](t-validation/sync-schema-check.txt) | 0 |
| Size budget | `python scripts/wasmer_size_budget.py` | [wasmer-size-budget.txt](t-validation/wasmer-size-budget.txt) | 0 |
| Parity | `python scripts/wasmer_parity.py` | [wasmer-parity.txt](t-validation/wasmer-parity.txt) | 0 |
| Full pytest (default venv) | `python -m pytest` | [pytest-full.txt](t-validation/pytest-full.txt) | 0 |
| Desktop smoke | `./wasmer/desktop/run-decide.sh` | [desktop-smoke.txt](t-validation/desktop-smoke.txt) | 0 |
| Desktop fail-open | `COMPASS_FAIL_OPEN_DEMO=missing ./wasmer/desktop/run-decide.sh` | [desktop-fail-open.txt](t-validation/desktop-fail-open.txt) | 0 |
| Registry auth | `wasmer whoami` | [wasmer-whoami.txt](t-validation/wasmer-whoami.txt) | non-zero (expected) |
| Credential boundary | `python -m pytest tests/test_credential_boundary.py -v` | [pytest-credential-boundary.txt](t-validation/pytest-credential-boundary.txt) | 0 |
| paid_sync default | `python -m pytest tests/test_paid_sync.py -v` | [pytest-paid-sync-default.txt](t-validation/pytest-paid-sync-default.txt) | 0 |
| paid_sync sibling venv | compressor engine venv + `PYTHONPATH=src:../comPREssOR/engine/src` | [pytest-paid-sync-compressor-venv.txt](t-validation/pytest-paid-sync-compressor-venv.txt) | 1 (expected) |

Pytest `tests/test_wasmer_desktop_packaged.py` (part of the 185) re-wrote B3 timestamps only:

- [s-desktop-mobile/desktop-evidence.json](s-desktop-mobile/desktop-evidence.json) `captured_at` → `2026-09-08T04:23:44Z`
- [s-desktop-mobile/desktop-packaged-vs-loose.txt](s-desktop-mobile/desktop-packaged-vs-loose.txt)
- [s-desktop-mobile/desktop-registry.txt](s-desktop-mobile/desktop-registry.txt) still `rc=1`, runtime NOT_RUN

## Results summary

| Scenario | Expected | Actual | Result | Evidence |
|---|---|---|---|---|
| Schema checksum guard | 10 passed | 10 passed in 0.04s | PASS | [pytest-schema.txt](t-validation/pytest-schema.txt) |
| Three schema copies one digest | `7fe7ea117c…` × 3 | same digest, `--check` exit 0 | PASS | [sync-schema-check.txt](t-validation/sync-schema-check.txt) |
| Browser cdylib ≤ 150 KB | ≤ 150000 | 103980 | PASS | [wasmer-size-budget.txt](t-validation/wasmer-size-budget.txt) |
| SHA256SUMS match on-disk | actual == expected | MATCH, `errors: []` | PASS | same |
| Python vs wasm parity | `ok: true` | `ok: true`, fail-open cases listed | PASS | [wasmer-parity.txt](t-validation/wasmer-parity.txt) |
| Default full pytest | honest count | **185 passed, 0 failed** | PASS (default venv) | [pytest-full.txt](t-validation/pytest-full.txt) |
| Desktop local `.webc` | decide `urn:mg:model:cheap` | that id, `fail_open: false` | PASS | [desktop-smoke.txt](t-validation/desktop-smoke.txt) |
| Fail-open demo | `snapshot_missing` | `fail_open: true`, reason `snapshot_missing` | PASS | [desktop-fail-open.txt](t-validation/desktop-fail-open.txt) |
| `wasmer login` | not present | `Not logged in registry wasmer.io` | NOT_RUN (honest) | [wasmer-whoami.txt](t-validation/wasmer-whoami.txt) |
| Sibling `test_paid_sync` | still broken | `AttributeError: 'str' object has no attribute 'lineage'` at `bundle.py:117` | FAIL / **NOT_FIXED** | [pytest-paid-sync-compressor-venv.txt](t-validation/pytest-paid-sync-compressor-venv.txt) |

## Stage grades (verified against the tree; not inflated)

| Stage | Grade | Why | Evidence |
|---|---|---|---|
| A1–A3 consolidation | **FULL** | Canonical `docs/FRAMEWORK.md`; `PROTOTYPE.md` superseded banner; ground truth in `PLANS.md` / `docs/README.md`; schema digest + packaging guard | [p-consolidation/README.md](p-consolidation/README.md); this-run schema + `--check` |
| B1 registry publish | **NOT_RUN** | No login; `compass` namespace unclaimed; no fake publish | [wasmer/PUBLISH-NOT_RUN.md](../wasmer/PUBLISH-NOT_RUN.md); [q-wasmer-publish/README.md](q-wasmer-publish/README.md); [wasmer-whoami.txt](t-validation/wasmer-whoami.txt) |
| B1 local `.webc` | **FULL** | Manifest at repo-root `wasmer.toml`; packaged run still decides | [q-wasmer-publish/evidence.json](q-wasmer-publish/evidence.json); [desktop-smoke.txt](t-validation/desktop-smoke.txt) |
| B2 browser `@wasmer/sdk` | **PARTIAL** | SDK 0.11.0 local guest FULL in prior capture; registry `compass/decide` NOT_RUN; Playwright **not** re-run here | [r-browser-sdk/README.md](r-browser-sdk/README.md); [r-browser-sdk/evidence.json](r-browser-sdk/evidence.json) |
| B3 desktop | **PARTIAL** | Local `.webc` default FULL (re-smoked); packaged≡loose (pytest refresh); registry-by-name code present, runtime NOT_RUN | [desktop-smoke.txt](t-validation/desktop-smoke.txt); [s-desktop-mobile/README.md](s-desktop-mobile/README.md); [s-desktop-mobile/desktop-registry.txt](s-desktop-mobile/desktop-registry.txt) |
| B4 mobile | **PARTIAL** | iOS Simulator prior run matches Python reason codes; Android NOT_RUN (no SDK); Simulator **not** re-run here | [s-desktop-mobile/mobile-hosts-summary.json](s-desktop-mobile/mobile-hosts-summary.json); [s-desktop-mobile/mobile-ios-simulator.json](s-desktop-mobile/mobile-ios-simulator.json); [s-desktop-mobile/mobile-android.json](s-desktop-mobile/mobile-android.json); commit `305609a` |

### A1–A3 tree check (this session)

- `docs/FRAMEWORK.md` exists, status **Canonical**, ADR 0001–0007 as current.
- `PROTOTYPE.md` banner: **HISTORICAL — origin brief**; points at `docs/FRAMEWORK.md`.
- `PLANS.md` line 4 and `docs/README.md` line 6 name `docs/FRAMEWORK.md` as ground truth.
- Canonical schema `src/compass/schema/model-graph.v1.json` digest `7fe7ea117cf40a692d9d62907a722a529cfcd437ab43873d4d8bf16d86c3bae0` shared with both mirrors.
- Stale `wasmer/desktop/wasmer.toml` path: **already corrected** in `docs/WASMER.md` and `docs/WASMER-DEPLOYMENT.md`. File `wasmer/desktop/wasmer.toml` is absent. No docs edit required this session.

## Environment matrix

| Environment | Prerequisite | Command / artifact | Grade |
|---|---|---|---|
| CLI / Python (this machine) | `.venv` | full pytest + schema + sync | **FULL** (185 passed) |
| Wasmer CLI local `.webc` | CLI 7.4.0, local package | `run-decide.sh` | **FULL** |
| Wasmer CLI registry-by-name | `wasmer login` + published `compass/decide` | `wasmer whoami`; desktop-registry.txt | **NOT_RUN** |
| Browser Playwright / Zone A | Chromium + prior B2 capture | [r-browser-sdk/](r-browser-sdk/README.md) | **PARTIAL** (prior; not re-run) |
| iOS Simulator | Xcode + simctl | [mobile-ios-simulator.json](s-desktop-mobile/mobile-ios-simulator.json) | **PARTIAL** (prior; not re-run) |
| Android emulator | Android SDK | [mobile-android.json](s-desktop-mobile/mobile-android.json) | **NOT_RUN** |
| Sibling comPREssOR engine venv | engine `.venv` + `chat_compressor` | paid_sync diagnostic | **FAIL** (pre-existing, NOT_FIXED) |

## Pytest counts (honest)

**Default comPASS `.venv` (the required full run):**

```
185 passed in 4.01s
```

`tests/test_schema.py`: **10 passed**.
`tests/test_paid_sync.py` in that venv: **5 passed**.
`tests/test_credential_boundary.py`: **12 passed**.
Collected total: **185** tests.

This is **not** the same environment as the Part A capture (`1 failed, 182 passed`). Here `chat_compressor` does not import (`ModuleNotFoundError: safetensors`), so `compass.bundle.export_bundle` uses the local free fallback and the test stays green.

**Sibling engine (diagnostic, expected failure, not fixed):**

```
FAILED tests/test_paid_sync.py::test_manual_compass_bundle_api_stays_free
AttributeError: 'str' object has no attribute 'lineage'
  ../comPREssOR/engine/src/chat_compressor/bundle.py:117
```

`compass.bundle.export_bundle` passes a graph-root **string** into compressor `export_bundle(store: StateStore, ...)`. Graded **NOT_FIXED** / out of scope (ADR 0002/0003). This session did not change `tests/test_paid_sync.py`.

## Size budget and parity (this run)

**Size budget:** `ok: true`. `compass_core_bg.wasm` **103980** bytes ≤ **150000**. All `SHA256SUMS` keys MATCH, including Path-B `eni6ma/demo-wasm/v1/eni6ma_wasm.wasm` (digest-checked only, not size-capped). Side effect: [j-wasmer-packaging/size-budget.json](j-wasmer-packaging/size-budget.json) now includes that eni6ma row (B1 deferred this refresh to validation).

**Parity:** `ok: true`. Fail-open lines:

```
core decide fail-open: snapshot_missing → default
core decide fail-open: snapshot_corrupt → default
core decide fail-open: no_candidates → default
```

## Outer `.webc` fingerprint vs module trust root

| Artifact | sha256 | Role |
|---|---|---|
| `test-results/q-wasmer-publish/compass-decide-0.1.0.webc` | `fe2dfc91893d692cb350ae92dee38a6c71bd669fd1fd847359f0fab2ffe8b5d9` | B1 recorded wrapper |
| repo-root `compass-decide-0.1.0.webc` (used by smoke) | `ee7fab4d7ac38a6519e9207a7b138d05a487a1b46fc758c9c3d3f0eb3637c7b5` | current wrapper (258019 bytes either way) |
| `wasmer/artifacts/compass-decide.wasm` | `e77301bed6f3bcdf8541ba7256cb6a4e58e1da62d7a98edb52fa27bdc1fee553` | **trust root** (MATCH) |
| `wasmer/artifacts/compass_core_bg.wasm` | `9ad58acccd85e361baf9a789cdd82e95cb264dd9ddc9691236200c6ceb2507db` | **trust root** (MATCH) |

Wrapper drift is documented in `wasmer/PUBLISH-NOT_RUN.md` (readme/license embed). Not a SHA256SUMS violation. `wasmer/artifacts/PACKAGE-DIGESTS.json` still stores the B1 wrapper hash; modules remain the authority.

## Locked invariants (still hold)

| Invariant | Status | Evidence |
|---|---|---|
| No `CURSOR_API_KEY` on the hook path | HOLD | Sibling `hook_cli.py` header: "Never requires CURSOR_API_KEY." comPASS [pytest-credential-boundary.txt](t-validation/pytest-credential-boundary.txt): core/route/serve do not import `compass.probe.credentials`; wasmer tree has no credential-module refs. |
| Fail-open | HOLD | Parity fail-open lines; desktop demo `fail_open: true` / `snapshot_missing`; Route tests inside the 185. |
| Digest-as-trust-root | HOLD | Size-budget `sha256_actual == sha256_expected`; iOS prior report `digest_match: true` on the same cdylib hash. |
| Size budget ≤ 150 KB browser cdylib | HOLD | 103980 ≤ 150000 |
| No fake green | HOLD | Registry publish NOT_RUN; Android NOT_RUN; Playwright/iOS not claimed as re-run; sibling paid_sync reproduced as FAIL |

CSP + COOP/COEP (not re-probed in a browser this session): `services/browser-client/nginx.conf` still has `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Embedder-Policy: require-corp`, `worker-src 'self' blob:`, `blob:` on `script-src`, Wasmer origins on `connect-src`. Prior live header dump: [r-browser-sdk/evidence.json](r-browser-sdk/evidence.json) `isolated_headers`.

## B2 / B4 prior artifacts (cited, not re-run)

**B2** ([evidence.json](r-browser-sdk/evidence.json), recorded `2026-09-08T03:54:29.637Z`):

- `sdk_npm`: 0.11.0; isolated `crossOriginIsolated` true; host/webc/python grades FULL; fail-open fallback with isolation off still decides `urn:mg:model:cheap`; `registry_compass`: NOT_RUN.

**B4** ([mobile-hosts-summary.json](s-desktop-mobile/mobile-hosts-summary.json)):

- iOS Simulator PARTIAL: `fixture_min` → `urn:mg:model:cheap`; missing → `snapshot_missing`; `digest_match: true`.
- Android NOT_RUN: `"reason": "Android SDK missing"`.

## Convergence tracker

| Iter | Phase | Fix | Criteria | Status |
|---|---|---|---|---|
| 1 | Validate + Prove | none (no breakage that this todo is allowed to fix) | offline guards 5/5 this run; registry/Android still NOT_RUN by design | **CONVERGED** (offline/local) |

Halt conditions: divergence no; oscillation no; iteration limit n/a.

## Commit gate

| Check | Result |
|---|---|
| All hard offline criteria | YES (schema, size, parity, default pytest, desktop local smoke) |
| Registry publish | NO — NOT_RUN by design |
| Android | NO — NOT_RUN by design |
| Proof report | YES (this file) |
| User authorized commit | YES (validation todo: commit proof) |
| Docker | N/A for this todo (no image rebuild) |

## Fixes this session

None. No feature re-implementation. Stale `wasmer/desktop/wasmer.toml` docs were already fixed by earlier commits. Leftover untracked `scripts/APPLY_HANDOFF.sh`, `scripts/push_dockerignore.sh`, `scripts/ship_challenge_pr.sh`, `scripts/ship_handoff.sh` left untracked. Dirty `test-results/h-session-polish/` left unstaged (not this todo).

## Re-run instructions

```bash
cd <comPASS repo root>
# use the project venv
.venv/bin/python -m pytest tests/test_schema.py -v
.venv/bin/python scripts/sync_schema.py --check
.venv/bin/python scripts/wasmer_size_budget.py
.venv/bin/python scripts/wasmer_parity.py
.venv/bin/python -m pytest
./wasmer/desktop/run-decide.sh
COMPASS_FAIL_OPEN_DEMO=missing ./wasmer/desktop/run-decide.sh
wasmer whoami   # expect: Not logged in registry wasmer.io until a human logs in

# sibling failure (do not treat default-venv green as a fix):
PYTHONPATH=src:../comPREssOR/engine/src \
  ../comPREssOR/engine/.venv/bin/python -m pytest \
  tests/test_paid_sync.py::test_manual_compass_bundle_api_stays_free -v --tb=short
```

Browser (not run this session):

```bash
cd wasmer/browser && npm install && npx playwright install chromium
cd <repo root>
COMPASS_SMOKE_CHANNEL=chrome node scripts/wasmer_browser_smoke.mjs
COMPASS_ZONEA_PYTHON=1 COMPASS_SMOKE_CHANNEL=chrome node scripts/wasmer_browser_sdk_smoke.mjs
```

Mobile (not run this session): `./scripts/validate-wasmer-mobile.sh`

## Conclusion

**Overall grade:** **PARTIAL** (program) — **CONVERGED** for the offline/local path.

- Offline/local: schema, size budget, parity, default pytest (185 passed), desktop `.webc` smoke, fail-open demo — **FULL** this run.
- Registry `compass/decide` publish and Android — **NOT_RUN** by design, not faked.
- Browser SDK and iOS Simulator — **PARTIAL** from prior stage artifacts; not re-executed here.
- Sibling `test_paid_sync` compressor path — **FAIL / NOT_FIXED**.

**Evidence-backed claims:** all rows in the results table link to an artifact.
**Fixes:** none.
**Next (human):** `wasmer login` + claim `compass` + `wasmer publish .` per `wasmer/PUBLISH-NOT_RUN.md`; Android SDK for B4; optional compressor-side bundle API mismatch (out of this repo).

## Provenance

| Section | Source | Type |
|---|---|---|
| Schema / sync / size / parity / pytest / desktop | `test-results/t-validation/*` | Live capture 2026-09-07 PT |
| B1 publish NOT_RUN | `wasmer/PUBLISH-NOT_RUN.md`, `test-results/q-wasmer-publish/` | Prior stage + this-run `wasmer whoami` |
| B2 browser | `test-results/r-browser-sdk/` | Prior capture; Playwright not re-run |
| B3 desktop packaged≡loose | `test-results/s-desktop-mobile/desktop-*` | Prior + pytest timestamp refresh |
| B4 iOS / Android | `test-results/s-desktop-mobile/mobile-*` | Prior; Simulator/SDK not re-run |
| A1–A3 | `docs/FRAMEWORK.md`, `PROTOTYPE.md`, `test-results/p-consolidation/` | Tree check + this-run schema guards |
