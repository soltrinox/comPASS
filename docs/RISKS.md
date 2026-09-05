# comPASS Risk Register

**Product:** comPASS (sister to comPREssOR)  
**Related:** [`CHARTER.md`](CHARTER.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`STACK.md`](STACK.md)

| ID | Risk | Impact | Mitigation | Owner track |
|---|---|---|---|---|
| R1 | Probe economics (models × classes × reps) dominate savings | Thesis failure | Thompson pruning; canary-only unconditional probes | C |
| R2 | Provider terms restrict benchmarking / comparative publication | Legal / managed-graph scope | Per-provider terms review before probe daemon aimed | E + C |
| R3 | Cross-hop reward attribution unsolved | Tier 4 policy wrong | Persist RouteDecision + recipient lineage; no claim of solved credit | C + B CC-1 |
| R4 | Bundled IDE auto-selection improves | Addressable market narrows | Compete on portability + governance, not generic quality | E |
| R5 | API churn on catalog sources | Maintenance drag | Adapter layer per source; contract tests | C ingest |
| R6 | Implementing against CHAT-COMPRESSOR 0.1.3 | Reintroduce personal paths; wrong version | Hard ban; master decision-working-copy; canonical only `soltrinox/comPREssOR` @ 0.2.0 | Master / E |
| R7 | Silent hop bugs (dedup / skip / warmup) | Tier 4 ships broken | Track B M1 scripted hop test | B |
| R8 | Wasmer module receives provider keys | Credential leak in browser | Host ABI deny; Probe native-only; Route+Graph **read** only in WASM | D |
| R9 | Paywalling accuracy | Trust + corpus death | Charter free-tier correctness rule; never paywall accuracy | E |
| R10 | Identical-text marketing claim | False advertising | Equivalence **band** language only (outcome-equivalence, never identical text) | E |
| R11 | Route raises into Agent Chat | Blocks user prompts | Fail-open MUST; advisory ignore on stale/malformed | C + B CC-9 |
| R12 | Probe shares hook process | Credential / latency coupling | Sibling repo; Probe **never on prompt path** | C / Arch |

### Notes

- **R6 / R7 / R8** are explicit program risks: wrong tree, silent hop defects, WASM key leakage.
- Scoring remains `quality − λ·cost` with bandits over `(TaskClass, ModelVersion)`; exhaustive probing is the failure mode (R1).
- In-Cursor Agent Chat stays advisory only (no model field in hooks) — overstating enforcement is a messaging risk owned with R10/E.
