# ADR 0005 — ENI6MA-gated browser agent

**Status:** Accepted  
**Date:** 2026-09-06 (PT)  
**Deciders:** Rosario (product owner)  
**Track:** Phase 3 architecture  
**Supersedes (product runtime):** Track D sidecar Probe deploy story; Cursor/IDE advisory as enforcement; Wasmer Edge FastAPI+Postgres as primary appliance  

---

## Context

Phase 1–2 delivered offline `compass-router` (Route / Graph / Probe planes, Wasmer decide artifacts, hop-safe comPREssOR) under a deploy story that kept Probe and provider keys in native sidecars and treated Cursor Agent Chat as an advisory surface. Wasmer platform capabilities and product intent have moved:

- `@wasmer/sdk/browser` can run pinned Python (and nested sandboxes) **in the tab**.  
- Outbound work can be mediated by a **host JS bridge** (and optional WISP for guest TCP).  
- ENI6MA Foundry / Control / Gate provides challenge–proof ceremonies over twin-circuit binaries with SHA-256 fingerprints.  
- Product owner directed: **no Cursor/IDE integration**, **browser-based only**, policies change **only** via ENI6MA ceremony; agents may start on manual / cron / event / poll under already-bound policy; LLM replies drive code via fence-first extract then tool/JSON fallback into Wasmer Python.

We need a single accepted decision so `ARCHITECTURE.md`, `STACK.md`, and `WASMER.md` stop describing sidecars and IDE hooks as the target runtime.

## Options

| # | Option | Notes |
|---|---|---|
| A | **Wasmer Edge appliance** (FastAPI + managed Postgres; fold Probe/proxy/comPREssOR into one Edge app) | Strong for multi-tenant SaaS; **not** browser-only; conflicts with “each tab = appliance” and air-gap page-recall delivery |
| B | **Track D cut** — Route/Graph WASM read-only; Probe/proxy/comPREssOR native sidecars; Cursor advisory | Matches Phase 1–2 docs; keeps keys off browser; **rejected** as product runtime by owner |
| C | **Cursor-integrated** advisory / hop path as primary UX | Hooks cannot enforce model selection; owner dropped IDE product integration |
| D | **Browser-only Wasmer agent + ENI6MA Gate + JS bridge egress** | One tab = one appliance; ceremony-bound policy; fence→exec in guest Python |

## Decision

**Accept option D.**

1. **Runtime:** Product control plane and execution live in-tab via `@wasmer/sdk/browser` (zone A). Host JS is glue (zone B).  
2. **Authority:** ENI6MA Foundry twin-circuits; Control burn-before-validate; Gate wraps `policy.update`, `agent.schedule`, `run_python`, LLM/tool/egress. Circuit binary local-first or URL fetch with **SHA-256 (+ length) fail-closed**.  
3. **Triggers:** Manual, in-tab cron, event, endpoint poll — start only under already ceremony-bound policy.  
4. **Egress:** Deny-by-default **JS bridge**; optional WISP only if guest needs TCP.  
5. **Code path:** LLM reply → markdown fences first → tool/JSON fallback → Gate `run_python` → write `main.py` → Wasmer Python.  
6. **Persistence:** Guest SQLite/memory (+ optional IndexedDB bridge). Edge Postgres is **not** the Phase 3 product store.  
7. **Non-goals:** Cursor/IDE primary path; native sidecars as default; multi-tenant Edge control plane as the agent itself.

## Consequences

- Rewrite [`../ARCHITECTURE.md`](../ARCHITECTURE.md) around zones A/B/C and ENI6MA (done with this ADR).  
- Mark Track D “sidecar Probe” and Cursor-hook process diagrams in [`../STACK.md`](../STACK.md) / [`../WASMER.md`](../WASMER.md) as **historical / superseded for product runtime**; keep artifact/ABI facts.  
- Implementation spine outstanding: `circuitLoader` + pin store, Gate-wrapped `wasmerRunner`, ceremony UX, in-tab triggers, page-recall artifact manifest, Verify/CI for replay/binding.  
- Phase 3 plans should target the browser appliance, not Edge `app.yaml` as the agent host.  
- Probe live keys remain a hard gate for live Observatory; offline fixtures are the default browser path.

## Acceptance

Accepted by Rosario via chat 2026-09-06 (PT): browser-only Wasmer sandbox agent; ENI6MA ceremony for policy; JS bridge egress; fence-then-fallback extract into Wasmer Python.
