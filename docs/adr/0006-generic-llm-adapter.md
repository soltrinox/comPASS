# ADR 0006 — Generic LLM adapter (decide / catalog / proxy override)

**Status:** Accepted  
**Date:** 2026-09-06 (PT)  
**Deciders:** Rosario (product owner)  
**Track:** Phase 3 — browser agent + serve plane  
**Depends on:** ADR 0005 (browser ENI6MA agent); comPREssOR hop-safe compression  

---

## Context

Callers need one ingress that can (1) let comPASS pick a weighted catalog model, (2) pin a linked catalog model, or (3) override to an arbitrary LLM endpoint (IP/domain/port/path)—i.e. act as a smart proxy. Mid-session hops must keep context via comPREssOR forward injection, not shared KV caches across models. Phase 1–2 `compass.serve.proxy` only decides then optionally forwards to a single `COMPASS_PROXY_UPSTREAM`; it does not yet express catalog pin vs per-request proxy override cleanly for the browser agent.

## Options

| # | Option | Notes |
|---|---|---|
| A | Separate endpoints per mode | More surface area; clients fork |
| B | **Single `/v1/chat/completions` + `compass` extension** | One OpenAI-shaped client; mode by payload |
| C | Header-only routing (`X-Compass-*`) | Easy to strip; worse for typed SDKs |

## Decision

**Accept B.** Documented in [`../API.md`](../API.md) §6.

1. Priority: **proxy override** → **catalog pin** → **decide**.  
2. Persist `RouteDecision` with `selection_mode` ∈ `{decide, catalog, proxy_override}`.  
3. comPREssOR handles hop-safe forward text when the target model changes.  
4. Browser egress: JS bridge + Gate; deny-by-default for override hosts.  
5. Extend `compass.serve.proxy` / add `compass.serve.adapter` rather than a new wire protocol.

## Consequences

- `docs/API.md` §6 is normative for clients.  
- Implementation plan: Phase 3 Track O (generic adapter).  
- Cursor enforcement rows demoted; adapter is the primary enforcement target.  
- Tests: mode resolution matrix, strip `compass` on forward, compress-on-hop hook, allowlist for override.

## Acceptance

Accepted by Rosario via chat 2026-09-06 (PT).
