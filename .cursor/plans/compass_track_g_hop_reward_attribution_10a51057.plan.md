---
name: comPASS Track G — Hop reward attribution
overview: Deepen retroactive reward attribution across hops using trajectory ids and delayed reward joins on RouteDecision — record policies, not a solved credit-assignment claim.
todos:
  - id: attribution-design-doc
    content: "Write design doc for trajectory/episode/counterfactual-later policies; explicitly state credit assignment is NOT solved"
    status: completed
  - id: trajectory-id-schema
    content: "Extend RouteDecision / Observation join fields with trajectory_id + hop_index; keep model-graph.v1 additive"
    status: completed
  - id: delayed-reward-recorder
    content: "Implement delayed reward recorder that joins outcomes onto prior RouteDecision nodes by trajectory_id"
    status: completed
  - id: retroactive-write-path
    content: "Graph write path for retroactive attribution with bitemporal supersede; never mutate Route hot path latency budget"
    status: completed
  - id: policy-trajectory-episode
    content: "Document and code policy switches: trajectory-level vs episode-level attribution; stub hook for counterfactual-later"
    status: completed
  - id: join-correctness-tests
    content: "Tests for join correctness — missing reward, late reward, multi-hop chain, fail-open when ids absent"
    status: completed
  - id: bandit-update-hook
    content: "Optional bandit posterior update from joined rewards without claiming optimality; gated feature flag"
    status: completed
  - id: proof-artifacts
    content: "Emit test-results/g-reward-attribution/ proof log linking schema + tests"
    status: completed
isProject: true
---

# comPASS Track G — Hop reward attribution

## Purpose

Deepen **reward attribution across hops**. The schema is already **RouteDecision-ready** (CC-1 recipient meta + persisted decisions). This track designs and implements **retroactive attribution recording** (trajectory ids, delayed reward join) so later analysis and bandit updates can re-attribute outcomes — **without claiming solved credit assignment**.

**Ground truth:** `src/compass/score/reward.py`, `RouteDecision` persistence (Tier 3), comPREssOR CC-1 `route_decision_id` / recipient lineage, prototype §13–§14, Phase 1 master non-claim on credit assignment.

**Depends on:** Track F schema hooks for live Observation stream preferred; can begin design + offline join tests immediately after Phase 1. Does not modify comPREssOR source (reads CC-1 fields only).

## Locked defaults

- Fail-open: missing trajectory ids ⇒ skip attribution, never block Route.
- Probe never on prompt path; attribution writer is async / post-hoc.
- No keys in WASM.
- Equivalence = outcome band, not identical text.
- **Explicit non-claim in docs and UI copy:** credit assignment across hops is **not solved**.

## Deliverable paths

```
comPASS/
  docs/
    schema/reward-attribution.v1.md     # NEW — policies
    adr/0003-reward-attribution.md      # NEW optional ADR
  schema/model-graph.v1.json            # additive fields only
  src/compass/
    score/reward.py                     # deepen
    score/attribution.py                # NEW
    graph.py                            # join/supersede helpers
  tests/test_reward_attribution.py      # NEW
  test-results/g-reward-attribution/
```

## Acceptance / test criteria

1. Design doc states three policies: **trajectory**, **episode**, **counterfactual-later** (stub), and the non-claim.
2. Additive schema validates; old fixtures still load.
3. Join tests: reward arriving after N hops updates the correct RouteDecision chain; orphan rewards logged not crashed.
4. Hot-path `decide()` p95 unaffected (no synchronous network/reward wait) — microbenchmark or unit proof.
5. Bandit update (if enabled) is feature-flagged and reversible via bitemporal supersede.
6. Proof folder with re-run instructions.

## Dependencies

| Depends on | Why |
|---|---|
| Phase 1 RouteDecision + CC-1 | Join keys exist |
| Track F (parallel-ok after schema hooks) | Live Observation richness |
| Unblocks H (session proofs can attach trajectory ids), N (governance audit trail) | |

## Explicit non-goals

- Solving multi-agent / multi-hop credit assignment.
- Counterfactual evaluation product (stub only).
- Changing compressor reward surfaces inside comPREssOR.
- Identical-text equivalence metrics.
