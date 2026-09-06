# ADR 0007 — agy behind ENI6MA circuit Gate

**Status:** Accepted
**Date:** 2026-09-06 (PT)
**Deciders:** Rosario (product owner)
**Track:** Phase 3 — browser agent + local LLM bridge
**Depends on:** ADR 0005; ADR 0006; services/agy-bridge

---

## Context

ADR 0005 requires ENI6MA Gate (SHA-256 pin + challenge/proof) before policy-sensitive egress. The local OpenAI-shaped agy-bridge spawns Google Antigravity CLI (agy --print) with no provider keys in-process. Without a Gate, any loopback client could drive agy. We need digest-pinned circuit load (mirror/cache), fail-closed mismatch, and a validation seam that can start as a stub and later bind the real ENI6MA WASM ABI.

## Options

| # | Option | Notes |
|---|---|---|
| A | Gate only in-browser; bridge trusts loopback | Weak: any local process can POST |
| B | Bridge runs Gate before agy (cache + allowlisted fetch + digest + validate stub) | Matches ADR 0005; air-gapped after first cache |
| C | Out-of-process Gate daemon | Extra moving part for a thin local bridge |

## Decision

**Accept B.**

1. Ingress: POST /v1/chat/completions reads body.compass.circuit (also top-level circuit).
2. Cache: COMPASS_CIRCUIT_CACHE or ~/.compass/circuits/; files named by sha256 hex; url-index.json maps URL to sha.
3. Fetch (miss): HTTPS hosts raw.githubusercontent.com and github.com only; blob URLs normalized to raw; optional url+.sha256 sidecar.
4. Digest: recompute SHA-256; sidecar or client pin mismatch → HTTP 403, never spawn agy.
5. Validate: WebAssembly.compile/instantiate; eni6maValidate stub (non-empty proof + load OK). Missing proof allowed in DEV (AGY_GATE_DEV=1 or AGY_FAIL_OPEN) as mode digest_only.
6. Response: strip compass/circuit from CLI path; include compass.gate { cached, sha256, source, validated, mode }.
7. No circuit: pass-through (mode no_circuit) unless AGY_GATE_REQUIRED=1.

## Consequences

- Implement services/agy-bridge/src/circuitGate.js + wire in server.js.
- Document request shape/env in services/agy-bridge/README.md; pointer in docs/API.md.
- Real ENI6MA ABI replaces eni6maValidate without changing Gate HTTP contract.
- Smoke: cache miss then hit; wrong sha256 → 403.

## Acceptance

Accepted by Rosario via chat 2026-09-06 (PT): full ENI6MA circuit Gate on local agy-bridge before agy.
