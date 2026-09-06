---
name: comPASS Phase 3 Track O — Generic LLM adapter
overview: Implement the normative generic LLM adapter (decide / catalog pin / proxy override) on the OpenAI chat-completions ingress, with comPREssOR hop-safe forward injection and browser bridge hooks per API.md §6 and ADR 0006.
todos:
  - id: o-api-freeze
    content: Treat docs/API.md §6 + ADR 0006 as frozen contract; add JSON Schema for compass extension if useful
    status: pending
  - id: o-mode-resolver
    content: "Implement selection_mode resolver: proxy_override > catalog > decide; persist RouteDecision.selection_mode"
    status: pending
  - id: o-extend-proxy
    content: Extend compass.serve.proxy (or new compass.serve.adapter) to honor compass.target / target_url / model_version_id; strip compass before forward
    status: pending
  - id: o-catalog-endpoints
    content: Resolve catalog ModelVersion → upstream base URL from Graph attrs; wire weighted candidates from store
    status: pending
  - id: o-compressor-hop
    content: On model change / compress.hop, call comPREssOR hop-safe forward inject before outbound; join trajectory_id
    status: pending
  - id: o-bridge-allowlist
    content: Browser JS bridge allowlist + Gate stub for proxy override hosts (deny-by-default)
    status: pending
  - id: o-tests
    content: "Tests: mode matrix, strip compass, dry-run, fallback_to_decide, fail-open; evidence under test-results/o-generic-adapter/"
    status: pending
  - id: o-docs-plans
    content: Link Track O from PLANS.md Phase 3; note ARCHITECTURE §10
    status: pending
isProject: true
---

# comPASS Phase 3 Track O — Generic LLM adapter

## Purpose

Ship the **generic adapter** locked in ADR 0006 / `docs/API.md` §6:

1. **Decide** — weighted Graph catalog via Route.  
2. **Catalog pin** — user-selected linked model.  
3. **Proxy override** — explicit scheme/host/IP/port/path (smart proxy).  

comPREssOR owns cross-LLM forward text for hops (KV-cache continuity without shared cache).

## Ground truth

- `docs/API.md` §6  
- `docs/adr/0006-generic-llm-adapter.md`  
- `docs/ARCHITECTURE.md` (adapter + browser zones)  
- Existing: `src/compass/serve/proxy.py`, `src/compass/serve/sdk.py`, `src/compass/route/decide.py`  
- Compressor: `soltrinox/comPREssOR` @ hop-safe main  

## Locked defaults

- Single ingress: `POST /v1/chat/completions`.  
- Mode priority: override → catalog → decide.  
- Fail-open on decide/catalog errors; transport errors on bad override unless `fallback_to_decide`.  
- Strip `compass` before upstream.  
- No keys in WASM; browser egress via JS bridge + Gate (ADR 0005).  
- Dry-run when no upstream / bridge denied (tests).  

## Deliverable paths

```
comPASS/
  src/compass/serve/adapter.py          # NEW mode resolver + handle
  src/compass/serve/proxy.py            # delegate to adapter / share forward_upstream
  src/compass/serve/sdk.py              # optional catalog pin helpers
  wasmer/browser/bridge.js              # NEW or extend — egress allowlist
  tests/test_generic_adapter.py         # NEW
  test-results/o-generic-adapter/
  docs/API.md                           # DONE (contract)
  docs/adr/0006-generic-llm-adapter.md  # DONE
```

## Acceptance

1. Unit tests for all three modes + priority conflicts.  
2. Forward path never leaks `compass` key to upstream JSON.  
3. Hop path invokes compressor mock/spy when model changes.  
4. Override to non-allowlisted host denied in browser policy fixture.  
5. Evidence folder with dry-run and (optional) local upstream smoke.  

## Order

`o-api-freeze` → `o-mode-resolver` → `o-extend-proxy` ∥ `o-catalog-endpoints` → `o-compressor-hop` → `o-bridge-allowlist` → `o-tests` → `o-docs-plans`.

## Out of scope

- Reminting ENI6MA circuits  
- Live Probe keys  
- Cursor/IDE enforcement  
