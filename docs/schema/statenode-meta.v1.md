# StateNode.meta recipient fields (CC-1)

**Contract for Track B.** Spec only — Track B owns code in `handle.py` / `store.py` on canonical `soltrinox/comPREssOR` @ **0.2.0**. Never implement against `CHAT-COMPRESSOR`.

**Product:** comPASS (sister to comPREssOR)  
**Purpose:** Record which model consumed/produced a turn so hop safety (CC-2–CC-5), reward re-attribution, and `route_decision_id` joins work. Additive and backward compatible.

## Fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `recipient_id` | string | no (absent ⇒ 0.2.0 behavior) | Served model id consuming the forward payload |
| `recipient_version` | string | no | Version / fingerprint when known |
| `route_decision_id` | string | no | URN of `RouteDecision` node when routed by comPASS |
| existing | | | Keep `tool_status`, `tokenizer_id` |

## Compatibility

- **Additive.** Existing state directories without these keys must round-trip unchanged and behave exactly as engine **0.2.0**.
- **Round-trip.** Fields MUST survive lineage reload through `StateStore` / `PersistentAgentHandle.step` persistence.
- Absent `recipient_id` ⇒ all hop-aware paths (CC-2–CC-5) keep pre-hop (0.2.0) semantics.
- No machine-specific absolute paths in compressor code examples.

## Example `meta` object

```json
{
  "tool_status": "stub",
  "tokenizer_id": "hashed-ngram",
  "recipient_id": "cursor-grok-4.6-high-fast",
  "recipient_version": "cn_4a91f0",
  "route_decision_id": "urn:mg:routedecision:a1b2c3"
}
```

## Related

- [`../API.md`](../API.md) — `RouteDecision` persistence and advisory `route_decision_id`
- [`model-graph.v1.json`](model-graph.v1.json) — `RouteDecision` node kind
- Prototype §14 CC-1
