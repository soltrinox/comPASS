# Session summary — comPASS prototype specification

**Date:** 2026-09-03
**Deliverable:** `comPASS/PROTOTYPE.md` (7,700 words)
**Mode:** Exploration and specification only — no code changes to either repository.

## What was produced

A prototype specification for `comPASS`, a capability-routed model selection engine positioned as a sibling to the `comPREssOR` context compressor. The document has two halves as requested: product strategy, tiering, and positioning (Part I), and architecture, integration mechanism, and required compressor modifications (Part II).

## Findings from the code audit that shaped the design

These were established by reading the source, not assumed.

1. **Model hopping is possible because the forward payload is model-agnostic text.** `translate/vocab_bridge.py` carries the comment "Compact frozen decode table so Cursor SDK always receives discrete text," and every `sample_text` return is `SampledPayload(kind="text", ...)`. Hop cost is bounded by `CHAT_COMPRESSOR_FORWARD_BUDGET`, not transcript length. This is the product's structural advantage.

2. **Routing cannot be enforced from inside Cursor Agent Chat.** `hook_cli.fail_open_default` fixes the return shapes — `beforeSubmitPrompt` returns `{"continue": true}` plus optional `additional_context`. There is no model field. In-IDE integration is advisory only.

3. **Three latent defects break silently under model hopping**, all live in canonical `0.2.0`:
   - Dedup suppression is keyed per session, not per recipient (`load_inject_history(self._agent_dir())` → `recent_line_hashes`), so a new model receives a payload with holes.
   - `pack_forward`'s skip path can return an empty payload, giving a newly arrived model zero context.
   - `adaptive_budget` scales down with session `t`, starving a model swapped in late.
   A scan of `engine/src/chat_compressor/` confirms no recipient or model awareness anywhere in the engine.

4. **The state lineage records no recipient.** `StateNode.meta` is `{"tool_status": "stub", "tokenizer_id": "hashed-ngram"}`. This is the root cause of the three defects above and the prerequisite for reward attribution.

5. **The tensor index is not currently quantized.** `StateStore.save` writes `float32` safetensors. Quantization is new work needed for cross-machine sync, not an existing property.

6. **`estimate_tokens` is `(len + 3) // 4`.** A chars/4 approximation cannot carry a cost-efficiency claim across models with different tokenizers.

7. **`ctx-graph.v1` should not be widened.** Node kinds and edge relations are fixed by both JSON schema `enum` and a runtime `ValueError`. A sibling `model-graph.v1.json` is correct. The bitemporal pattern (`valid_start` / `valid_end` / `status` / `supersede`) should be borrowed, because endpoint drift under a stable model id is exactly a supersession event.

## Repository correction

`/Users/rosario/work/CHAT-COMPRESSOR` is **not a git repository** and is at engine `0.1.3`. The canonical remote is `git@github.com:soltrinox/comPREssOR.git` (`/Users/rosario/work/comPREssOR`, branch `main`, engine `0.2.0`, clean tree). Canonical is a *sanitized* line — it has removed hardcoded personal identifiers that the working copy still contains (`FORBIDDEN_WORKSPACE = Path("/Users/rosario/work")` in `live_models.py`, `rosario` in the `graph.py` identifier regex). All compressor modifications target the canonical repo and must avoid reintroducing machine-specific absolute paths.

## Deliberately unresolved

- **Reward attribution across hops.** Credit assignment when a cheap model's error surfaces on a later expensive turn. The design records enough to re-attribute retroactively rather than claiming a solution.
- **"Same output regardless of model."** Scoped to task-outcome equivalence within a measured confidence band on oracle-bearing task classes. Identical text is not achievable and is not claimed.

## Next actions (none taken)

Ten numbered compressor changes (CC-1 … CC-10) with file targets, risk, and tests are tabled in §14.3. Four milestones with falsifiable exit criteria are in §17.3. Six open decisions, including the product name, are in Appendix A. No repository was created and nothing was pushed.
