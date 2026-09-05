# ADR 0004 — Reward attribution recording (Track G)

**Status:** Accepted  
**Date:** 2026-09-05 (PT filing)  
**Deciders:** Rosario (repo owner); Track G (W-G) executed  
**Track:** G (Hop reward attribution)  
**Cites:** Risk R3; Phase 1 non-claim on credit assignment; CC-1 join keys

---

## Context

Tier 3 already persists `RouteDecision` nodes. Multi-hop sessions need a way to
attach **delayed** outcomes to prior decisions so bandits and audits can
re-attribute later. Claiming solved cross-hop credit assignment would overstate
the product (R3).

## Decision

1. Add additive join fields (`trajectory_id`, `hop_index`, `episode_id`) on
   RouteDecision attrs; keep `model-graph/v1` additive.
2. Implement post-hoc delayed-reward join with bitemporal **supersede** (never
   mutate Route `decide()` latency budget).
3. Document three policies: **trajectory**, **episode**, **counterfactual-later**
   (stub). Always record `credit_assignment_solved: false`.
4. Gate optional bandit updates behind `COMPASS_ATTRIBUTION_BANDIT_UPDATE` (default off).

## Consequences

- Operators can re-score history from joined records.
- Fail-open when ids absent; orphan rewards logged not crashed.
- Credit assignment remains an open research / product problem — Track G does
  **not** close R3 as "solved".
