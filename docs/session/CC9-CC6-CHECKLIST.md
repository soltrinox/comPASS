# CC-9 / CC-6 session polish checklist (Track H)

**Product:** comPASS + comPREssOR  
**Goal:** Prove advisory handoff (CC-9) and pluggable token costing (CC-6) are test-ready for real Cursor Agent Chat — with fail-open — without requiring a live IDE when the scripted harness can prove the path.

**Ground truth:** comPREssOR @ `44460ba` (`hook_cli.py`, `tokens.py`); comPASS `src/compass/serve/advisory.py`; [`../API.md`](../API.md); comPREssOR `docs/HOOK_CONTRACT.md`.

---

## Grades

| Grade | Meaning |
|---|---|
| **FULL** | Automated or live path asserted green |
| **PARTIAL** | Path works with documented gaps (e.g. no live IDE log yet) |
| **NOT_RUN** | Blocker noted; do not claim success |

---

## A. Scripted harness (prefer this first)

From the comPASS checkout:

```bash
# Uses local comPREssOR at ../comPREssOR (override with COMPRESSOR_ROOT)
.venv/bin/python scripts/session_polish_harness.py
# Evidence → test-results/h-session-polish/
```

The harness:

1. Writes a fresh `compass-advisory/v1` JSON via `compass.serve.advisory.write_advisory`.
2. Points `CHAT_COMPRESSOR_ADVISORY_PATH` at that file.
3. Imports comPREssOR `chat_compressor.hook_cli` and asserts:
   - `_compose_additional_context` / `beforeSubmitPrompt` include `COMPASS_ADVISORY`
   - stale / missing / corrupt advisory ⇒ `continue: true` and **no** `COMPASS_ADVISORY` (fail-open)
4. Exercises CC-6: `register_counter` → `count_tokens` uses accurate path; `packing_tokens` stays on `estimate_tokens`.

Optional: run compressor unit suites in-place (no comPASS source change):

```bash
cd ../comPREssOR/engine && .venv/bin/python -m pytest tests/test_cc9_advisory.py tests/test_cc6_tokens.py -q
```

---

## B. Manual Cursor Agent Chat (once)

Do this once on Rosario's machine to grade the **live** UI path. Scripted harness alone is enough for CI/regression; this closes the IDE loop.

### Prep

1. Confirm chat-compressor hook shim is installed (`~/.cursor/hooks/chat-compressor.sh`) and fail-open.
2. Note state dir from `~/.cursor/chat-compressor.env` → `CHAT_COMPRESSOR_STATE_DIR`.
3. Optional: set `CHAT_COMPRESSOR_ADVISORY_PATH` to an absolute path, else use `$STATE_DIR/advisory/latest.json`.

### CC-9 — fresh advisory appears

1. From comPASS (adjust `dest` to your state root):

   ```bash
   .venv/bin/python - <<'PY'
   from pathlib import Path
   from compass.serve.advisory import write_advisory
   dest = Path.home() / ".cursor" / "chat-compressor-state" / "advisory" / "latest.json"
   write_advisory(
       dest,
       {
           "task_class_id": "multi_file_refactor",
           "selected_model_version_id": "urn:mg:modelversion:session-polish",
           "scores": {},
           "route_decision_id": "urn:mg:routedecision:session-h",
       },
       model_id="cursor-session-polish-demo",
       provider="cursor",
       ttl_seconds=600,
       rationale="Track H manual check: advisory should appear in additional_context.",
       strict=True,
   )
   print("wrote", dest)
   PY
   ```

2. Open **Cursor Agent Chat** in a workspace with the compressor hook active.
3. Submit a prompt that triggers `beforeSubmitPrompt` (any non-trivial user message).
4. Inspect hook / session log or model-visible context for a line starting with `COMPASS_ADVISORY:` and `recommended_model=cursor-session-polish-demo`.
5. Paste the relevant snippet into `test-results/h-session-polish/session-manual-ide.log.txt` (operator local; may be gitignored).

### CC-9 — fail-open (corrupt / missing)

1. Overwrite the advisory file with `{not-json` **or** delete it.
2. Submit another Agent Chat prompt.
3. Confirm chat **continues** (no hard failure). Context must **not** contain `COMPASS_ADVISORY:`.
4. Record outcome in the evidence pack (`fail_open_manual`: FULL/PARTIAL/NOT_RUN).

### CC-6 — cost counters (registration check)

In-IDE Cursor does not currently surface a tokenizer registry UI. Verify with the harness or a one-liner against comPREssOR:

```bash
cd ../comPREssOR/engine && .venv/bin/python - <<'PY'
from chat_compressor.tokens import (
    register_counter, count_tokens, packing_tokens, clear_counters,
)
from chat_compressor.metrics import estimate_tokens
clear_counters()
text = "hello world " * 10
register_counter("demo-tok", lambda t: 99 if t else 0)
assert count_tokens(text, tokenizer_id="demo-tok") == 99
assert packing_tokens(text) == estimate_tokens(text)  # packing never uses registry
clear_counters()
print("CC-6 ok: accurate path vs packing estimate")
PY
```

**How to register a tokenizer counter (API):**

| Step | API | Notes |
|---|---|---|
| Register | `register_counter(tokenizer_id, callable)` | `callable(text) -> int` |
| Cost path | `count_tokens(text, tokenizer_id=...)` | Uses registry; fail-open to estimate on error |
| Packing path | `packing_tokens(text)` | **Always** `metrics.estimate_tokens` (chars/4) |
| Unregister | `unregister_counter` / `clear_counters` | Tests should clear |
| Optional HF | `try_hf_counter("gpt2")` | Returns `None` if transformers missing (NOT_RUN) |

**PARTIAL note:** If no recipient `tokenizer_id` is registered in a live session, cost path falls back to `estimate_tokens` (chars/4). That is by design — document missing registrations rather than claiming accurate billing.

---

## C. Locked invariants (do not violate)

- Fail-open: missing/stale/corrupt advisory never blocks Agent Chat.
- Probe/keys never in the hook process.
- Advisory is **advisory only** — no model field forcing in hook return shapes.
- Track H does **not** modify comPREssOR `.py` engine source.

---

## D. Evidence locations

| Artifact | Path |
|---|---|
| Harness evidence | `test-results/h-session-polish/evidence.json` |
| Harness logs | `test-results/h-session-polish/session-*.txt` |
| This checklist | `docs/session/CC9-CC6-CHECKLIST.md` |
| Harness script | `scripts/session_polish_harness.py` |
