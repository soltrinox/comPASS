# comPASS docs (Track A)

Track A deliverables. Implementation is Tracks B–D. Product/GTM is Track E. **Do not edit compressor source from this track.**

**Product placeholder:** comPASS (sister to comPREssOR)  
**Ground truth:** [`../PROTOTYPE.md`](../PROTOTYPE.md)  
**Canonical compressor:** `soltrinox/comPREssOR` @ **0.2.0** — never `CHAT-COMPRESSOR`

## Index

| Doc | Purpose |
|---|---|
| [`CHARTER.md`](CHARTER.md) | Problem, wedge, tiers 1–4, free vs paid, non-claims, success metrics |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | **Phase 3:** browser Wasmer agent zones; ENI6MA Gate; planes remapped; extract→exec loop |
| [`adr/0005-eni6ma-gated-browser-agent.md`](adr/0005-eni6ma-gated-browser-agent.md) | **Accepted:** browser-only + ENI6MA ceremony; supersedes sidecar/Cursor runtime |
| [`API.md`](API.md) | Route API + **generic LLM adapter** (§6: decide/catalog/proxy override) |
| [`adr/0006-generic-llm-adapter.md`](adr/0006-generic-llm-adapter.md) | **Accepted:** single completions ingress; three selection modes |
| [`STACK.md`](STACK.md) | Python 3.11+, SQLite/JSON/…; Phase 1–2 process layout marked superseded by ADR 0005 |
| [`WASMER.md`](WASMER.md) | Wasmer artifacts/ABI + Phase 3 browser appliance notes |
| [`RELEASE.md`](RELEASE.md) | Track L: version scheme, tag policy, TestPyPI/PyPI publish (no secrets) |
| [`abi/host-abi.v1.md`](abi/host-abi.v1.md) | Host ABI v1 (storage/clock/log/config; keys forbidden) |
| [`INTEGRATION.md`](INTEGRATION.md) | CC-1–CC-10 touchpoints; ingestion; classification reuse; bundle pointer |
| [`session/CC9-CC6-CHECKLIST.md`](session/CC9-CC6-CHECKLIST.md) | Track H: CC-9 advisory + CC-6 token counter session polish checklist + harness |
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
- **Phase 3 runtime:** browser-only Wasmer agent + ENI6MA Gate ([ADR 0005](adr/0005-eni6ma-gated-browser-agent.md)); no Cursor/IDE product path
- Egress: host JS bridge deny-by-default; optional WISP; no ambient provider keys in static page
- Historical Track D: Route+Graph WASM read + Probe sidecar — superseded for product deploy
