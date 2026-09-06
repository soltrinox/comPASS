# comPASS API — Route plane, advisory & generic LLM adapter

**Product:** comPASS (sister to comPREssOR)  
**Planes:** Probe / Graph / Route (fail-open)  
**Runtime (Phase 3):** browser Wasmer agent — [`ARCHITECTURE.md`](ARCHITECTURE.md), [`adr/0005-eni6ma-gated-browser-agent.md`](adr/0005-eni6ma-gated-browser-agent.md)  
**Adapter decision:** [`adr/0006-generic-llm-adapter.md`](adr/0006-generic-llm-adapter.md)  
**Related:** [`INTEGRATION.md`](INTEGRATION.md), [`schema/statenode-meta.v1.md`](schema/statenode-meta.v1.md)

This document defines the **logical** Route plane API, fail-open semantics, `RouteDecision` persistence, the **generic LLM adapter** (decide / catalog / proxy override), the CC-9 advisory file contract (historical Cursor path), and enforcement vs advisory.

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

> **Historical (Phase 1–2).** Cursor/IDE is **not** a Phase 3 product surface ([ADR 0005](adr/0005-eni6ma-gated-browser-agent.md)). CC-9 remains the compressor file handoff contract for any host that still injects advisory context. Prefer the **generic adapter** (§6) for enforcement.

Cursor hook return shapes (when used) have **no model field**:

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
| 1 | **Generic LLM adapter** (`POST /v1/chat/completions`) | 3–4 | **Yes** — primary Phase 3 path | Decide / catalog / proxy override; §6 |
| 2 | Advisory file (CC-9) | 2 | **No** — advise only | Historical Cursor / any inject host |
| 3 | Cursor SDK wrapper | 3 | Deprecated for product | No IDE integration (ADR 0005) |

Do not document Cursor hooks as capable of enforcing model selection.


---

## 4. Escalation and envelopes (API notes)

- **Escalation ladder** (oracle-bearing classes only): try cheap candidate → detect verifiable failure → retry stronger. Not applied to unverifiable tasks.
- **Budget envelopes:** session / project / org scope; Route raises λ as consumption approaches the limit (gradual degradation). Enforcement (not mere reporting) is a paid-tier differentiator.

---

## 5. Related schemas

- Capability graph: [`schema/model-graph.v1.json`](schema/model-graph.v1.json) (`RouteDecision` node kind)
- Compressor recipient meta (CC-1): [`schema/statenode-meta.v1.md`](schema/statenode-meta.v1.md) — `route_decision_id` joins advisory/routing to lineage

---

## 6. Generic LLM adapter (normative, Phase 3)

One ingress. OpenAI-compatible shape. comPASS selects or honors a target, optionally runs **comPREssOR** hop-safe forward injection, then forwards (or dry-runs).

### Endpoint

```
POST /v1/chat/completions
Content-Type: application/json
```

Body is a normal chat-completions object (`messages`, optional `model`, `stream`, …) plus optional **comPASS routing extensions** under `compass` (extensions MUST be stripped or ignored by upstreams that do not understand them; the adapter removes `compass` before forward).

### Selection modes

Exactly one mode applies per request, resolved in this order:

| Priority | Mode | How the client asks | Behavior |
|---|---|---|---|
| 1 | **Proxy override** | `compass.target` present (see below) | Use explicit scheme/host/port/path; skip catalog decide for *selection*; still persist `RouteDecision` with `selection_mode: "proxy_override"` |
| 2 | **Catalog pin** | `compass.model_version_id` **or** `model` matching a linked Graph `ModelVersion` / served id | Pin that catalog entry’s upstream; `selection_mode: "catalog"` |
| 3 | **Decide (default)** | Neither override nor resolvable pin | Route `classify → candidates → score → decide` over weighted Graph posteriors; `selection_mode: "decide"` |

Fail-open (MUST): on decide/catalog resolution failure → configured default endpoint + `fail_open: true` + `default_reason`. Proxy override with unreachable host returns transport error to the client (routing already succeeded); do not silently re-decide unless `compass.fallback_to_decide: true`.

### `compass` extension object

```json
{
  "compass": {
    "selection_mode": "decide",
    "model_version_id": "urn:mg:modelversion:…",
    "target": {
      "scheme": "http",
      "host": "192.168.1.50",
      "port": 8080,
      "path": "/v1/chat/completions",
      "model": "local-llama"
    },
    "fallback_to_decide": false,
    "compress": {
      "enabled": true,
      "hop": true,
      "recipient_model_id": null
    },
    "session_id": "…",
    "trajectory_id": "…"
  }
}
```

**`compass.target` fields (proxy override)**

| Field | Required | Notes |
|---|---|---|
| `host` | yes | IP or domain |
| `port` | no | Default 443 for `https`, 80 for `http` |
| `scheme` | no | `https` (default) or `http` |
| `path` | no | Default `/v1/chat/completions` |
| `model` | no | Rewrites outbound `model` if set |

Alternate shorthand (also accepted): `compass.target_url` as an absolute URL (`http://10.0.0.5:8080/v1/chat/completions`). If both `target` and `target_url` are set, `target_url` wins.

**Catalog pin** may use either:

- `compass.model_version_id` (URN), or  
- top-level `model` equal to a Graph `served_id` / catalog alias.

### Weighted catalog (decide mode)

Candidates come from Graph `ModelVersion` nodes with `status=active` and valid bitemporal interval. Weights / posteriors are bandit state (`quality`, `cost`, optional arm prior). Score remains:

```
score(m, c) = E[quality(m, c)] − λ · E[cost(m, c)]
```

Linked endpoints on each node (or provider policy) supply the upstream base URL used after decide. No provider keys in Route/WASM; browser egress uses the host JS bridge + Gate ([ADR 0005](adr/0005-eni6ma-gated-browser-agent.md)).

### comPREssOR coupling (MUST)

When the adapter changes model mid-session (hop), or `compass.compress.hop` is true, call **comPREssOR** to build hop-safe forward text / recipient meta **before** the outbound request. That package travels with the prompt so the target LLM receives continuity without assuming a shared KV cache across models. Do not reimplement compressor logic inside the adapter.

Reference: `soltrinox/comPREssOR` hop-safe path (CC-1 recipient meta, CC hop legality). Join via `route_decision_id` / `trajectory_id` on `StateNode.meta` when present.

### Response

Upstream OpenAI-shaped body on success. Adapter MAY add a non-breaking `compass` object on dry-run or when `compass.include_decision: true`:

```json
{
  "compass": {
    "selection_mode": "decide",
    "selected_model": "…",
    "upstream": "https://…/v1/chat/completions",
    "route_decision": { },
    "compressed": true,
    "dry_run": false
  }
}
```

### Dry-run

If no upstream can be resolved and dry-run is enabled (default in tests / when bridge denied), return an OpenAI-shaped stub describing the selection without calling a model—same spirit as today’s `compass.serve.proxy` dry-run.

### Security

- Proxy override hosts are **deny-by-default** unless allowlisted in Gate-bound policy or explicitly ceremonied.  
- Strip `compass` from the outbound JSON.  
- Never put long-lived provider keys in the static page or WASM module.

### Mapping to code (implementation target)

| Concern | Module (planned / extend) |
|---|---|
| Mode resolution | `compass.serve.adapter` (new) or extend `compass.serve.proxy` |
| Decide / catalog | `compass.route.decide`, GraphStore |
| Forward | `forward_upstream` + browser JS bridge |
| Compress / hop inject | comPREssOR API from serve plane |
| Persist | `RouteDecision` with `selection_mode` |

---

## 7. Local agy-bridge + ENI6MA circuit Gate

Local OpenAI-shaped bridge (`services/agy-bridge`) may sit behind or beside the generic adapter for air-gapped `agy --print` egress. Normative Gate behavior (circuit URL/sha256/proof, allowlisted fetch, cache, fail-closed digest, `compass.gate` response) is in [ADR 0007](adr/0007-agy-behind-eni6ma-gate.md) and `services/agy-bridge/README.md`. Request extension: `compass.circuit` (or top-level `circuit`) with `url`, `sha256`, optional `proof` / `challenge_id`.

