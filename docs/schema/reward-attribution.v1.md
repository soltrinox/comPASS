# Reward attribution v1 (Track G)

**Product:** comPASS (sister to comPREssOR)  
**Status:** Recording policies — **not** a solved credit-assignment claim  
**Schema:** additive attrs on `RouteDecision` / `Observation` under `model-graph/v1`

## Explicit non-claim

> **Credit assignment across hops is NOT solved.**

comPASS records trajectory / episode / decision join keys and delayed rewards so
operators and later algorithms can **re-score** history. Shipping these joins does
**not** mean multi-hop or multi-agent credit assignment is correct, optimal, or
complete. UI and docs must keep this non-claim visible (see also risk R3).

## Join keys (additive)

| Field | On | Purpose |
|---|---|---|
| `trajectory_id` | RouteDecision attrs, Observation attrs | Groups hops in one multi-hop trajectory |
| `hop_index` | RouteDecision attrs | Order within a trajectory (0-based) |
| `episode_id` | RouteDecision attrs | Short episode / oracle grouping |
| `route_decision_id` | Observation / reward payload | Direct attach to one decision |
| `attributed_reward` | RouteDecision attrs (after join) | Recorded share × raw reward |
| `attribution_policy` | RouteDecision attrs (after join) | `trajectory` / `episode` / `counterfactual_later` |
| `credit_assignment_solved` | RouteDecision attrs (after join) | Always `false` |

Attrs remain `additionalProperties: true` on `model-graph/v1` — old fixtures load unchanged.

## Policies

### 1. Trajectory-level (`trajectory`)

Delayed reward joins **all** active `RouteDecision` nodes sharing `trajectory_id`.
Each hop records an **equal share** (`1/N`) for analysis. This is a **recording
convention**, not a claim that each hop deserved `1/N` of the outcome.

### 2. Short-episode / oracle (`episode`)

Joins hops sharing `episode_id`. Oracle convention: full reward share (`1.0`) on
the **terminal** hop (highest `hop_index`); earlier hops get `share=0` but still
receive an audit join row. Useful when an external oracle scores only the episode
end. Still **not** solved credit assignment.

### 3. Counterfactual-later (`counterfactual_later`)

**Stub only.** Returns `status=stubbed` and performs **no** graph write. Reserved
for a future counterfactual evaluation product. Non-goal for Track G.

## Fail-open

- Missing all join keys ⇒ `skipped` (never block Route).
- Join keys present but no matching RouteDecision ⇒ `orphaned` (logged, no crash).
- Attribution writer is **async / post-hoc** — never on the `decide()` hot path.
- Probe stays off the prompt path; no provider keys in WASM.

## APIs

- `compass.score.attribution.attach_delayed_reward` / `join_delayed_reward`
- `compass.score.reward.attach_reward_to_trajectory`
- `compass.score.reward.attach_reward_to_route_decision`
- `compass.graph.GraphStore.attribute_delayed_reward`
- Optional bandit update: feature flag `COMPASS_ATTRIBUTION_BANDIT_UPDATE` (default off),
  reversible via bitemporal supersede. **Does not claim optimality.**

## Equivalence

Outcome **band** equivalence only — never identical-text metrics (Charter / R10).

## Related

- ADR 0004 — Reward attribution recording
- `docs/RISKS.md` R3
- CC-1 `route_decision_id` / recipient lineage on compressor StateNode.meta
