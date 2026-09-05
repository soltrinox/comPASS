# comPASS docs (Track A)

Track A deliverables. Implementation is Tracks B–D. Product/GTM is Track E. **Do not edit compressor source from this track.**

**Product placeholder:** comPASS (sister to comPREssOR)  
**Ground truth:** [`../PROTOTYPE.md`](../PROTOTYPE.md)  
**Canonical compressor:** `soltrinox/comPREssOR` @ **0.2.0** — never `CHAT-COMPRESSOR`

## Index

| Doc | Purpose |
|---|---|
| [`CHARTER.md`](CHARTER.md) | Problem, wedge, tiers 1–4, free vs paid, non-claims, success metrics |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Probe / Graph / Route planes; Observatory / Advisor / Router / Session orchestrator; mermaid |
| [`API.md`](API.md) | Route classify/score/decide; fail-open; CC-9 advisory; enforcement targets |
| [`STACK.md`](STACK.md) | Python 3.11+, SQLite/JSON/safetensors/NumPy; Wasmer Route+Graph read; Probe native |
| [`WASMER.md`](WASMER.md) | Track D Wasmer runbook: core split, ABI, packaging status, fail-open parity |
| [`abi/host-abi.v1.md`](abi/host-abi.v1.md) | Host ABI v1 (storage/clock/log/config; keys forbidden) |
| [`INTEGRATION.md`](INTEGRATION.md) | CC-1–CC-10 touchpoints; ingestion; classification reuse; bundle pointer |
| [`RISKS.md`](RISKS.md) | Risk register (R1–R12) |
| [`schema/model-graph.v1.json`](schema/model-graph.v1.json) | Sibling capability-graph JSON Schema (`model-graph/v1`) — do not widen `ctx-graph.v1` |
| [`schema/statenode-meta.v1.md`](schema/statenode-meta.v1.md) | CC-1 recipient fields on `StateNode.meta` |

Machine-facing mirrors (byte-identical schema + bundle stub):

- `/Users/rosario/work/comPASS/schema/model-graph.v1.json`
- `/Users/rosario/work/comPASS/schema/bundle.v1.json`

## Locked invariants (quick)

- Planes: Probe (daemon, credentials, **NEVER on prompt path**) / Graph (bitemporal + bandit) / Route (hot path, **fail-open**)
- Tiers: 1 Observatory, 2 Advisor, 3 Router, 4 Session orchestrator
- Scoring: `quality − λ·cost`; Thompson/UCB over `(TaskClass, ModelVersion)`
- Bitemporal: `valid_start`, `valid_end`, `status` ∈ `{active, superseded, deprecated}`
- Equivalence: **outcome-equivalence band**, never identical text
- Wasmer: Route + Graph **READ** only; Probe native sidecar; **no provider keys in browser WASM**
- In-IDE Cursor Agent Chat: **advisory only** (no model field in hooks)
