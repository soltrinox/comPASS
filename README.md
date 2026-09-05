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

## C1 status (early cut)

Shipped:

- Package scaffold (`compass-router`) + CI workflow
- Packaged `model-graph.v1.json` + `GraphDocument` loader
- Graph store skeleton (SQLite + JSON) with fail-open reads
- Bandit interface stubs (Thompson / UCB) with fail-open defaults
- Route `classify` (keyword stub) + `decide()` fail-open
- Probe daemon **offline** skeleton: synthetic fixture corpus, dry-run runner
  (`COMPASS_PROBE_ALLOW_NETWORK` defaults OFF), canary → `GraphDocument.supersede`
- Credential boundary documented: keys never in Route/Graph; Probe-only later

**Not in C1:** Live provider probe HTTP, Tier 1–4 product surfaces, Tier 3 proxy, Wasmer (Track D).

## Explicit non-goals

- Do not rebuild LiteLLM / OpenRouter
- Do not widen `ctx-graph.v1`
- Do not put Probe inside the hook or WASM
- Do not hardcode machine-specific absolute paths in package source
