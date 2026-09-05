# comPASS (`compass-router`)

Working name **comPASS** — sibling engine to [comPREssOR](https://github.com/soltrinox/comPREssOR).  
Python package: **`compass-router`** (`requires-python >= 3.11`).

Capability-aware model routing over three planes and four tiers.  
Contracts and architecture live under [`docs/`](docs/).

## Docs (start here)

| Doc | Purpose |
| --- | --- |
| [`PROTOTYPE.md`](PROTOTYPE.md) | Ground-truth product prototype (§9–§17) |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Three planes, four tiers, credential boundary |
| [`docs/API.md`](docs/API.md) | Route plane API, fail-open, advisory contract |
| [`docs/STACK.md`](docs/STACK.md) | Stack + Wasmer boundary (Track D contract) |
| [`docs/schema/model-graph.v1.json`](docs/schema/model-graph.v1.json) | Capability graph schema (also packaged) |
| [`docs/RELEASE.md`](docs/RELEASE.md) | Version scheme, tags, TestPyPI / PyPI publish |
| [`CHANGELOG.md`](CHANGELOG.md) | Keep-a-Changelog for compass-router |

## Three planes

| Plane | Role | Credentials | Failure |
| --- | --- | --- | --- |
| **Probe** | Daemon: probes, observations, canary drift | Holds provider keys | **Never on the prompt path**; never blocks prompts |
| **Graph** | Bitemporal capability store + bandit posterior | None | Stale-read OK |
| **Route** | Classify → score → decide (hot path) | None | **Fail-open** to configured default |

**Probe stays out of the hot path.** Do not import `compass.probe.runner` from Route, hooks, or WASM. Provider keys never appear in Route/Graph modules.

## Scoring

```
score(m, c) = E[quality(m, c)] − λ · E[cost(m, c)]
```

Bandit probe allocation: Thompson sampling over `(TaskClass, ModelVersion)` (UCB fallback).

## Layout

```
src/compass/          # Python package
schema/               # model-graph.v1.json + bundle.v1.json (repo mirror)
docs/                 # Track A contracts (do not relocate)
tests/                # pytest
scripts/test-unit.sh  # local CI-shaped runner
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
# or: ./scripts/test-unit.sh
```

Default CI runs unit tests on Python 3.11/3.12 with **no provider keys**.

## Status (`0.1.0`)

Shipped (Phase 1 offline stack + Phase 2 tracks F–J / H / M / L plumbing):

- Package `compass-router` `0.1.0` — pure-Python sdist/wheel; see [`docs/RELEASE.md`](docs/RELEASE.md)
- Graph / Probe / Route planes; Route **fail-open**; Probe network gate default OFF
- Packaged `model-graph.v1.json`; Graph store (SQLite + JSON); Thompson / UCB stubs
- Tier 1–4 surfaces (Observatory / Advisor / Router proxy+SDK / session orchestrator)
- Probe-only credentials (Track M); gated live transports mocked in CI (Track F)
- Wasmer artifacts + browser/desktop smoke (Track J); **not** bundled in the wheel
- Hop reward attribution joins (Track G); CC-9/CC-6 session polish harness (Track H)

**Not claimed:** production SLA, solved credit assignment, unrestricted live benchmarking, PyPI production publish.

Install from git until a TestPyPI/PyPI upload is operator-approved:

```bash
pip install "compass-router @ git+https://github.com/soltrinox/comPASS.git@v0.1.0"
# or editable: pip install -e ".[dev]"
```

## Explicit non-goals

- Do not rebuild LiteLLM / OpenRouter
- Do not widen `ctx-graph.v1`
- Do not put Probe inside the hook or WASM
- Do not hardcode machine-specific absolute paths in package source
