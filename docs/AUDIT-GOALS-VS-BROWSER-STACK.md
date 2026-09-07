# Audit: product goals vs browser Wasmer stack

**Date:** 2026-09-07 (PT)  
**Scope:** Charter + Phase 3 ADRs 0005–0007 vs what is built for the browser-only appliance.  
**Related:** [CHARTER.md](CHARTER.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [WASMER-DEPLOYMENT.md](WASMER-DEPLOYMENT.md) · [adr/0005](adr/0005-eni6ma-gated-browser-agent.md) · [adr/0006](adr/0006-generic-llm-adapter.md) · [adr/0007](adr/0007-agy-behind-eni6ma-gate.md)

> Status labels: **Done** = shipped/testable · **Partial** = library or lab only · **Not done** = designed or blocked.

---

## A. Project & product goals (source of truth)

### A1. Charter problem / wedge
1. Route by **task type**, not global model ranking (price ≠ quality monotonically).  
2. Build a **posterior on the user’s own work** (personal probes), not public leaderboards.  
3. Treat model ids as **unstable** (bitemporal supersede on fingerprint break).  
4. Keep **portable memory** as discrete text via **comPREssOR** (hop costs forward budget, not full transcript).  
5. Free tier must stay useful and **never paywall correctness**.

### A2. Shippable tiers (1–4)
| Tier | Goal |
|---|---|
| **1 Observatory** | Live catalog + drift; useful without routing |
| **2 Advisor** | Classify + recommend (historically Cursor-advisory; Phase 3: not IDE-primary) |
| **3 Router** | Enforced routing at owned call sites (SDK / OpenAI proxy / envelopes) |
| **4 Session orchestrator** | Per-turn hop + `hop_legal` + capability-aware shaping (needs CC-1..CC-10) |

### A3. Planes
- **Probe** — credentials; never on prompt path  
- **Graph** — bitemporal store + bandit  
- **Route** — classify → score → decide; **fail-open**

### A4. Free vs paid
- **Free:** local Observatory/Graph/Route/proxy, manual bundle, own keys  
- **Paid:** automated sync, multi-model insertion bands, fleet graph, governance, team memory  

### A5. Non-claims
- Not identical text across models  
- Not solved hop credit assignment  
- Not OpenRouter/LiteLLM replacement  
- Not Cursor-hook enforcement (and Phase 3: **no IDE product path**)

### A6. Phase 3 Wasmer / ENI6MA goals (ADR 0005–0007)
6. **Browser-only appliance** (one tab = one agent); no Edge Postgres control plane.  
7. Policies / side effects only via **ENI6MA ceremony** (digest-pinned circuit).  
8. **Generic adapter:** decide / catalog / proxy_override + comPREssOR hop inject.  
9. LLM code path: fence-first → tool/JSON → Wasmer Python.  
10. **agy** stays native behind Gate-protected bridge (not inside Wasmer).  
11. Air-gap capable: local cache, deny-by-default egress.

### A7. Success milestones (charter M0–M4)
M0 recipient meta · M1 hop-safe payload · M2 catalog supersede · M3 advisory fail-open · M4 enforced RouteDecision + bundle — **largely met in Phase 1–2 offline stack**; live Probe/publish/mobile still gated.

---

## B. Goal → status map

| # | Goal | Status | Notes |
|---|---|---|---|
| 1 | Task-type routing | **Done (lib)** | Route decide + tests |
| 2 | Personal posterior / probes | **Partial** | Offline fixtures; **live Probe NOT_RUN** (no keys) |
| 3 | Bitemporal supersede | **Done** | Graph store + Observatory offline |
| 4 | Portable hop memory (comPREssOR) | **Done (sibling)** | CC-1..10 on comPREssOR; browser always-on inject **partial** |
| 5 | Free correctness | **Done (policy)** | Free/paid docs + spikes |
| T1 Observatory | **Partial** | Offline catalog yes; live smoke no |
| T2 Advisor | **Done → deprecated UX** | CC-9 exists; Cursor path dropped |
| T3 Router / adapter | **Done (engine)** | Track O adapter + proxy; browser UX thin |
| T4 Session hops | **Partial** | Orchestrator + hop legal in lib; full in-tab loop incomplete |
| ENI6MA ceremony UX (six-color) | **Not done** | No interactive 6-color UI |
| Digest-pin circuit load | **Done** | Path-B `circuitLoader` + bridge Gate |
| Cryptographic verify / burn ledger | **Not done** | DEMO-MINT prove-only; Gate = digest + `abi_probe` |
| Fence→Wasmer exec product loop | **Not done** | Designed; not Gate-wrapped product |
| agy-bridge + Docker | **Done (lab)** | `:8791` healthy; default **fake-agy** |
| Live Gemini via agy | **Partial** | Needs live-agy profile + host auth |
| Air-gap deny egress | **Done (testable)** | Empty allowlist / dry-run |
| Paid pillars | **Spike / test-ready** | Not production SaaS |
| Mobile Wasmer | **NOT_RUN** | Doc only |

---

## C. Browser deployment stack (what runs / would run in the tab)

```
Browser tab (one appliance)
├── Zone B — Host JS                         [PARTIAL product shell]
│   ├── COOP/COEP + page                     [stub pages exist]
│   ├── @wasmer/sdk/browser                  [designed; not full product boot]
│   ├── circuitLoader.js                     [DONE — digest fail-closed]
│   ├── wasmerRunner.js                      [DONE — minimal proof smoke]
│   ├── agent.html / agent.js                [DONE stub — NOT six-color UI]
│   ├── sandbox.js (compass decide wasm)     [DONE smoke]
│   ├── bridge.js (egress allowlist)         [DONE]
│   └── ceremony / six-color UI              [NOT STARTED]
│
├── Zone A — Wasmer guest                    [PARTIAL]
│   ├── compass_core_bg.wasm decide          [DONE artifact]
│   ├── pinned Python / agent loop           [DESIGNED — not full product]
│   ├── Route / Graph / adapter logic        [DONE in Python lib; in-guest packaging partial]
│   ├── comPREssOR in-process                [PARTIAL seam]
│   ├── extractCode → run_python             [NOT PRODUCT]
│   └── nested sandbox                       [NOT PRODUCT]
│
└── Host services (beside browser)           [LAB DONE]
    ├── Docker agy-bridge :8791              [DONE — Gate + fake-agy]
    ├── circuitGate cache/fetch/digest       [DONE]
    ├── real agy / Gemini                    [OPTIONAL / NOT DEFAULT]
    └── Control burn ledger                  [NOT DONE]
```

---

## D. Hierarchy audit (one sentence each)

**Working / testable now**
- **comPASS Route** — Classifies and scores models and fail-opens to a default without holding provider keys.  
- **comPASS Graph** — Stores bitemporal capability nodes and bandit posteriors for decide.  
- **Track O adapter** — Picks proxy_override, catalog pin, or decide on one completions ingress.  
- **compass_core_bg.wasm** — Runs decide-from-snapshot in the browser with no key imports.  
- **circuitLoader** — Fetches a circuit only if SHA-256 matches the authority pin.  
- **wasmerRunner** — Loads the DEMO-MINT package and runs `build_minimal_proof` after digest OK.  
- **agent.html stub** — Buttons to smoke ENI6MA proof and compass pin checks.  
- **bridge.js** — Deny-by-default host allowlist for browser egress.  
- **agy-bridge** — Loopback OpenAI-shaped proxy that Gates then calls agy/fake-agy.  
- **circuitGate** — Caches/fetches circuits, fail-closes on digest mismatch, ABI-probes the module.  
- **Docker Compose** — Brings agy-bridge up healthy on `:8791` for lab deploy.  
- **comPREssOR (sibling)** — Supplies hop-safe forward text so model switches don’t assume shared KV.

**Designed / incomplete**
- **Ceremony / six-color web UI** — Should let a human complete an interactive proof; **not built**.  
- **ENI6MA verify + burn-before-validate** — Should cryptographically validate and consume nonces; **stub / prove-only ABI**.  
- **In-tab policy store** — Should bind Gate-proven rules to the agent; **not productized**.  
- **Full Wasmer agent boot** — Should hydrate SDK+Python+packages and start triggers; **not a finished appliance**.  
- **Fence→exec loop** — Should extract model Python and run under Gate in Wasmer; **not shipped**.  
- **Live Observatory** — Should probe real providers into Graph; **blocked on keys**.  
- **Always-on hop compress** — Should call real comPREssOR on every model change; **hook only**.  
- **Live Antigravity** — Should use real `agy`/Gemini in Compose; **fake-agy is default**.

---

## E. Bottom line

| Question | Answer |
|---|---|
| Against **original charter** (tiers 1–4 offline)? | **Mostly achieved** for libraries/tests; live Probe/PyPI/mobile still open. |
| Against **Phase 3 browser sovereign agent**? | **Scaffold + Gate digest path ~½**; ceremony UX + verify + full agent boot **not ready to ship**. |
| What can you **test/deploy today**? | Docker bridge + Path-B digest/proof smoke + adapter/proxy dry-run — **lab**, not production agent. |
| Biggest gap vs “auth → instantiate agent in Wasmer”? | **Interactive six-color ceremony + real verify/burn + agent boot shell**. |

---

## F. Related docs

- Lifecycle / stack map: [`WASMER-DEPLOYMENT.md`](WASMER-DEPLOYMENT.md)
- Runtime architecture: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- Product charter: [`CHARTER.md`](CHARTER.md)
