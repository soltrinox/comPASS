# comPASS API — Route plane & advisory

**Product:** comPASS (sister to comPREssOR)  
**Planes:** Probe (never on prompt path) / Graph / Route (fail-open)  
**Related:** [`ARCHITECTURE.md`](ARCHITECTURE.md), [`INTEGRATION.md`](INTEGRATION.md), [`schema/statenode-meta.v1.md`](schema/statenode-meta.v1.md)

This document defines the **logical** Route plane API, fail-open semantics, `RouteDecision` persistence, the CC-9 advisory file contract, and the enforcement vs advisory distinction. Implementations land in Track C (engine) and Track B (CC-9 hook inclusion).

---

## 1. Route plane API (logical)

```
classify(request, graph_snapshot) -> TaskClass
candidates(task_class, constraints) -> [ModelVersion]
score(model_version, task_class, λ) -> float   # quality − λ·cost
decide(request, envelope, policy) -> RouteDecision | Default
```

### Semantics

| Call | Behavior |
|---|---|
| `classify` | Map prompt + current graph state to a `TaskClass` **before** any answer is known. Prefer over-provisioning on hard/uncertain classes. Reuse compressor featurizers (`extractive.keyword_set`, `chunks.chunk_text`, `rank.rank_chunks`) — do not invent a parallel featurizer in v1. |
| `candidates` | Filter `ModelVersion` nodes with `status=active` and valid interval containing now, by hard constraints: policy, data classification, context-window sufficiency, availability. |
| `score` | `E[quality] − λ · E[cost]` using Graph posterior; λ from envelope / outer loop. |
| `decide` | Score survivors; confidence-gate; envelope check; persist `RouteDecision`; return choice + machine-readable rationale. On failure → **Default**. |

### Hard requirements (normative)

1. **Bounded latency.** Target p95 **< 50 ms** for the decide path that blocks the caller.
2. **Fail-open (MUST).** Any exception, timeout, empty candidate set, or corrupt graph read → configured **default endpoint** + **logged reason**. Never raise into Agent Chat. The router must never be why a request fails.
3. **Persist `RouteDecision`.** Record model, task class, scores, λ, constraints applied, rationale, timestamp (and link via `selected` edge). Enables audit and later reward re-attribution.
4. **Confidence gating.** Overlapping quality intervals → prefer lower cost; do not pretend certainty.
5. **No provider keys** in the Route process or WASM module. Probe holds credentials; Probe is **never on the prompt path**.

### `RouteDecision` persistence (logical shape)

```json
{
  "id": "urn:mg:routedecision:…",
  "kind": "RouteDecision",
  "status": "active",
  "valid_start": "2026-09-04T00:00:00Z",
  "valid_end": null,
  "attrs": {
    "task_class_id": "urn:mg:taskclass:…",
    "selected_model_version_id": "urn:mg:modelversion:…",
    "scores": {"urn:mg:modelversion:…": 0.71},
    "lambda": 1.0,
    "constraints_applied": ["policy:local-secrets", "ctx_window"],
    "rationale": "highest score under envelope; intervals non-overlapping",
    "fail_open": false,
    "default_reason": null,
    "decided_at": "2026-09-04T00:00:00Z"
  }
}
```

When fail-open fires, still persist a decision with `fail_open: true` and `default_reason` set (e.g. `timeout`, `empty_candidates`, `corrupt_graph`, `exception`).

---

## 2. Advisory hook contract (CC-9)

Cursor hook return shapes are **unchanged** and have **no model field**:

- `beforeSubmitPrompt` → `{"continue": true}` (+ optional `additional_context`)
- `sessionStart` → `{"additional_context": ""}`

Therefore In-IDE Cursor Agent Chat is **advisory only**.

### File-based handoff

1. Router **service** (separate process; may talk to Graph; never shares Probe keys with the hook) writes a small advisory document under the compressor state root.
2. Suggested path (operator-configurable): `advisory/latest.json` relative to the agent/state root.
3. Compressor `_compose_additional_context` includes it when **fresh**; ignores when **stale, missing, or malformed** (fail-open).
4. Hook process **never** loads provider keys.

### Advisory file schema

```json
{
  "schema": "compass-advisory/v1",
  "written_at": "2026-09-04T18:00:00Z",
  "expires_at": "2026-09-04T18:05:00Z",
  "task_class": "multi_file_refactor",
  "recommendation": {
    "model_id": "cursor-grok-4.6-high-fast",
    "provider": "cursor",
    "model_version_id": "urn:mg:modelversion:8f2c1d"
  },
  "rationale": "Across your last 40 tasks of this class, X scored 0.82 at $0.11/task; Y scored 0.85 at $0.94/task.",
  "route_decision_id": "urn:mg:routedecision:…",
  "scores_summary": [
    {"model_id": "X", "quality_mean": 0.82, "n": 40, "est_cost_per_task": 0.11},
    {"model_id": "Y", "quality_mean": 0.85, "n": 40, "est_cost_per_task": 0.94}
  ]
}
```

**Freshness rule.** Include iff `expires_at` is in the future (host clock), JSON parses, and required fields are present. Otherwise ignore silently (log at debug). Missing/stale/corrupt advisory **MUST NOT** block Agent Chat.

Track B implements inclusion in `hook_cli.py`. This doc is the contract.

---

## 3. Enforcement targets

| # | Target | Tier | Enforcement? | Notes |
|---|---|---|---|---|
| 1 | Advisory inside Cursor | 2 | **No** — advise only | Hook has no model field |
| 2 | Cursor SDK wrapper | 3 | **Yes** — first real enforcement | Explicit model parameter on agent construction |
| 3 | OpenAI-compatible local proxy | 3–4 | **Yes** — broadest coverage | Owns provider credentials → lives in probe/route **service** process, **never** hook path |

Do not document Cursor hooks as capable of enforcing model selection.

---

## 4. Escalation and envelopes (API notes)

- **Escalation ladder** (oracle-bearing classes only): try cheap candidate → detect verifiable failure → retry stronger. Not applied to unverifiable tasks.
- **Budget envelopes:** session / project / org scope; Route raises λ as consumption approaches the limit (gradual degradation). Enforcement (not mere reporting) is a paid-tier differentiator.

---

## 5. Related schemas

- Capability graph: [`schema/model-graph.v1.json`](schema/model-graph.v1.json) (`RouteDecision` node kind)
- Compressor recipient meta (CC-1): [`schema/statenode-meta.v1.md`](schema/statenode-meta.v1.md) — `route_decision_id` joins advisory/routing to lineage
