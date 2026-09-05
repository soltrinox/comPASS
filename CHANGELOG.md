# Changelog

All notable changes to **compass-router** (the comPASS sibling engine) are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [SemVer](https://semver.org/) as described in [`docs/RELEASE.md`](docs/RELEASE.md).

## [Unreleased]

- Track N — paid pillars test-ready: `compass.sync` (paid automate / free manual), `compass.fleet` stub (opt-in), `compass.serve.governance` hooks; evidence `test-results/n-paid-pillars/`.
- Phase 2 **test-ready stack exit** flipped 2026-09-05 (PT) — F–N evidence present; **not** production-ready / SLA.

## [0.1.0] — 2026-09-05

First packaged cut of `compass-router` (`requires-python >= 3.11`). Pure-Python sdist/wheel; Wasmer artifacts stay in-repo and are **not** bundled into the wheel.

### Phase 1 — Offline stack (Tracks A–E)

- Package scaffold (`src/compass`) + CI (native pytest on 3.11/3.12).
- Graph / Probe / Route planes with **fail-open** Route defaults.
- Packaged `model-graph.v1.json` + `GraphDocument` loader; Graph store (SQLite + JSON).
- Bandit interface stubs (Thompson / UCB) with fail-open defaults.
- Route `classify` + `decide()` fail-open; Probe daemon offline skeleton (network gate default OFF).
- Credential boundary: provider keys never in Route / Graph / `compass.core` / WASM.
- Wasmer crate + `wasmer/artifacts/*.wasm` with Python fail-open parity (Track D).
- Docs: CHARTER, ARCHITECTURE, API, STACK, WASMER, ADRs 0001/0002.

### Phase 2 — Test-ready surfaces already merged

- Track I — Phase 1 plan-checkbox hygiene aligned with merged reality.
- Track K — KEEP archived 0.1.3 tree; ADR 0003 refuse rule.
- Track M — Probe-only OpenRouter / HF / Cursor credential loaders + import audit.
- Track F — gated live Probe/Observatory HTTP transports (mocked in CI; live smoke NOT_RUN).
- Track G — hop reward attribution joins (no credit-assignment claim).
- Track H — CC-9 advisory + CC-6 token session polish harness.
- Track J — headless Wasmer browser smoke, desktop shell, size-budget CI; mobile device farm NOT_RUN.

### Added (this release track)

- `docs/RELEASE.md` — version scheme, tag policy, TestPyPI / PyPI publish commands.
- GitHub Actions release workflow stub (`.github/workflows/release.yml`) — build on tag / manual dispatch; publish only when secrets + explicit input allow.
- Apache-2.0 `LICENSE` (matches compressor).
- Packaging metadata: authors, classifiers, project URLs, `twine` in the `dev` extra.

[Unreleased]: https://github.com/soltrinox/comPASS/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/soltrinox/comPASS/releases/tag/v0.1.0
