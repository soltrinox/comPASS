# comPASS Integration Playbook

**Product:** comPASS (sister to comPREssOR)  
**Canonical compressor:** `git@github.com:soltrinox/comPREssOR.git` @ engine **0.2.0**  
**Forbidden tree:** `CHAT-COMPRESSOR` (untracked, 0.1.3, pre-sanitization) — never implement against it  
**Ground truth:** [`../PROTOTYPE.md`](../PROTOTYPE.md) §11, §14–§15

Track A documents touchpoints. **Track B** owns compressor code. **Track C** owns the sibling engine. Do not modify compressor `.py` from this track.

**Sanitize:** no `/Users/rosario/...` paths in **code** that lands in the compressor. Canonical 0.2.0 already removed them; do not reintroduce. Docs may cite absolute paths for operator navigation only.

---

## 1. Where to check out (operators)

| Repo | Remote | Notes |
|---|---|---|
| Canonical compressor | `git@github.com:soltrinox/comPREssOR.git` | Branch `main`, engine `0.2.0` |
| Sibling product | this `comPASS` tree | Specs under `docs/`; engine scaffold Track C |
| Related distribution | `soltrinox/OPENCLAW-comPREssOR` | Do not confuse with canonical |

Checkout example (relative / portable — do **not** paste personal absolute paths into compressor source):

```bash
git clone git@github.com:soltrinox/comPREssOR.git
cd comPREssOR
git checkout main
# verify engine version is 0.2.0 in the package metadata
```

---

## 2. Compressor touchpoints (CC-1–CC-10)

Paths relative to `comPREssOR/engine`:

| ID | Files | Change |
|---|---|---|
| CC-1 | `src/chat_compressor/handle.py`, `store.py` | Recipient fields in `StateNode.meta` (`recipient_id`, `recipient_version`, `route_decision_id`) — see [`schema/statenode-meta.v1.md`](schema/statenode-meta.v1.md) |
| CC-2 | `handle.py`, `store.py` | Per-recipient inject ledger |
| CC-3 | `pack.py` | Recipient change resets suppression |
| CC-4 | `pack.py`, `handle.py` | Gate `allow_skip` on continuity |
| CC-5 | `pack.py`, `handle.py` | Per-recipient warmup counter |
| CC-6 | new `tokens.py` (+ `metrics.py` call sites) | Pluggable token counter |
| CC-7 | `handle.py` | `hop_legal()` |
| CC-8 | new `bundle.py` | Export/import portable bundle |
| CC-9 | `hook_cli.py` | Fail-open advisory inclusion ([`API.md`](API.md)) |
| CC-10 | `store.py` | Optional tensor quantization |

Compatibility: additive or env-gated. Absent recipient info, paths behave exactly as **0.2.0**. Fail-open: no change may let advisory/router failure block Agent Chat. Do **not** widen `ctx-graph.v1`.

---

## 3. Planes & credential boundary

| Plane | Integration note |
|---|---|
| **Probe** | Separate daemon; holds provider keys; **NEVER on the prompt path** |
| **Graph** | Written by Probe / ingest; read by Route; no provider keys |
| **Route** | Hot path; **fail-open**; SDK wrapper + proxy for enforcement; advisory file for Cursor |

Proxy owns provider credentials in the **service** process — never in the hook process or browser WASM ([`STACK.md`](STACK.md)).

In-IDE Cursor Agent Chat: **advisory only** (no model field in hooks).

---

## 4. Ingestion sources

| Source | Role | Reuse |
|---|---|---|
| Hugging Face Hub | Cards → **priors** (`README` front matter, `config.json`, tokenizer config) | Optional `hf` extra |
| OpenRouter / aggregators | Catalog + pricing + probe **substrate** | Consume; do not replace |
| Cursor model list | Served ids for Observatory / Advisor | Reuse `extract_model_ids` / `resolve_model_ids` from compressor `live_models.py` |

Identity: `(provider, served_id)` = `ModelVersion`; `version_of` → `Model` only when fingerprint agrees.

---

## 5. Classification reuse

Do **not** invent a parallel featurizer in v1. Reuse:

- `extractive.keyword_set`
- `chunks.chunk_text`
- `rank.rank_chunks`

Task classes seed from capability axes (prototype §4) and cluster from user history.

Scoring: `quality − λ·cost`. Bandits (Thompson/UCB) over `(TaskClass, ModelVersion)`.

---

## 6. Bundle format pointer

Prototype §15 layout (`bundle.v1/`):

```
bundle.v1/
  manifest.json
  graph.json              # ctx-graph/v1
  states/*.safetensors
  inject_ledger.json      # per-recipient (CC-2)
  lineage.json
```

Machine-facing stub outline: `comPASS/schema/bundle.v1.json` (forward-ref Track B CC-8 / §15). Full schema fleshed with Track B.

Equivalence under substitution: **outcome-equivalence band**, never identical text ([`CHARTER.md`](CHARTER.md)).

---

## 7. Operator checklist

1. Clone canonical comPREssOR @ 0.2.0 (not CHAT-COMPRESSOR).
2. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`API.md`](API.md).
3. Confirm Probe is a separate process; Route fail-open configured.
4. For Cursor: enable advisory file handoff only; do not expect hook model enforcement.
5. For enforcement: wrap SDK or run local proxy in the service process.
6. Track B lands CC-*; Track C implements Graph/Probe/Route; Track D Wasmer read path.

---

## References

- [`../PROTOTYPE.md`](../PROTOTYPE.md) §14 change summary and Appendix C path map
- comPREssOR `docs/HOOK_CONTRACT.md`, `schema/ctx-graph.v1.json` (do not widen)
- Sibling schema: [`schema/model-graph.v1.json`](schema/model-graph.v1.json)
