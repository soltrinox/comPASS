# comPASS Stack & Wasmer runtime

> **Superseded for product runtime (ADR 0005, 2026-09-06):** Phase 3 is the **browser-only ENI6MA-gated Wasmer agent** — see [`ARCHITECTURE.md`](ARCHITECTURE.md). The Cursor-hook / Probe-sidecar process layout below remains the Phase 1–2 engineering contract for offline `compass-router` libraries and CI; it is **not** the shipping appliance topology.


**Product:** comPASS (sister to comPREssOR)  
**Package name (until rename):** `compass-router`  
**Track D** implements the WASM cut; **this doc is the contract.**

---

## 1. Core stack (matches compressor)

| Layer | Choice |
|---|---|
| Language | **Python ≥ 3.11** (`requires-python >=3.11`) |
| Metadata store | **SQLite** |
| Graph documents | **JSON** (`model-graph/v1`) |
| Tensor payloads | **safetensors** |
| Scoring math | **NumPy** |
| Route plane deps | **No mandatory heavyweight dependency** |

Optional dependency groups (mirror compressor layout):

- `dev` — tests, lint, typecheck
- `hf` — Hugging Face Hub ingestion
- `sdk` — Cursor / OpenAI client wrappers for owned call sites

Probe plane may take additional deps (HTTP clients, aggregators); it is **not** latency-bound and is **never on the prompt path**.

---

## 2. Process layout

```
[ Cursor hook / Agent Chat ]  --fail-open advisory file-->  (no keys)
[ SDK wrapper / local proxy ] --decide--> Route --read--> Graph
[ Probe daemon ] --write observations--> Graph
         ^ holds provider credentials (native only)
```

- **Route** — hot path; fail-open to configured default; target p95 < 50 ms.
- **Graph** — bitemporal + bandit posterior; read path shared with Route.
- **Probe** — native sidecar / daemon; credentials; outbound HTTP; catalog fetch; canary execution.

---

## 3. Wasmer / WASM boundary (Track D)

| In WASM (Route + Graph **READ**) | Native sidecar only (**Probe**) |
|---|---|
| Classify, score, decide, graph snapshot read | Provider credentials |
| Bandit posterior **read** | Outbound probe HTTP |
| Fail-open default table | Catalog fetch / canary execution |

### Security MUST

- **No provider keys in the browser WASM module.** Host ABI must deny raw key material into the module.
- Host ABI imports (allowed): storage **read**, clock, config, log.
- Host ABI imports (forbidden): `keys.*`, raw secrets, unrestricted outbound HTTP from the module for probe execution; browser builds omit `fetch`.
- Route must stay in the **tens of ms** inside WASM.
- Versioning: module ABI **semver** paired with `model-graph/v1`.

### Implementation pointers (Track D)

- Python WASM-safe package: `src/compass/core/` (classify, score_read, decide_from_snapshot, snapshot, defaults, abi).
- Native sidecar marker: `src/compass/native/` (probe / ingest / serve remain excluded from WASM).
- Host ABI: [`docs/abi/host-abi.v1.md`](abi/host-abi.v1.md) + [`docs/abi/host-abi.v1.json`](abi/host-abi.v1.json).
- Deploy runbook + packaging surface: [`docs/WASMER.md`](WASMER.md), [`wasmer/README.md`](../wasmer/README.md).
- **Honest status:** no browser `.wasm` binary yet (Wasmer CLI not installed). Pure-Python boundary + fail-open tests stand in until the artifact lands.

**This document remains the contract; WASMER.md is the operator runbook.**

---

## 4. Persistence layout (logical)

```
compass-data/
  graph/
    model-graph.json          # model-graph/v1 document(s)
  meta.sqlite                 # indexes, envelopes, bandit state pointers
  tensors/                    # optional safetensors for embeddings / posteriors
  advisory/                   # written for CC-9 handoff (service side)
    latest.json
```

Exact on-disk paths are operator-configurable. Sample code and compressor-bound examples must **not** hardcode machine-specific absolute paths (e.g. no `/Users/rosario/...` in code that lands in comPREssOR).

---

## 5. Alignment with comPREssOR 0.2.0

- Same Python floor and optional-deps style.
- Same two-tier storage intuition (SQLite metadata + document/tensor files).
- Canonical compressor only: `git@github.com:soltrinox/comPREssOR.git` @ **0.2.0**. Never target `CHAT-COMPRESSOR`.
- Equivalence product claim remains **outcome-equivalence band**, never identical text.