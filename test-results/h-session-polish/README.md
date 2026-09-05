# Track H — session polish evidence

- `evidence.json` — grades FULL/PARTIAL/NOT_RUN for CC-9 and CC-6
- `session-harness.txt` — harness stdout (fresh advisory + fail-open + CC-6)
- `session-fail-open.txt` — fail-open summary (missing/corrupt/stale)
- `pytest-compass.txt` — full comPASS pytest (must stay green)
- `pytest-compressor-cc9-cc6.txt` — comPREssOR `test_cc9_advisory` + `test_cc6_tokens`
- Manual IDE: see `docs/session/CC9-CC6-CHECKLIST.md` §B (`cc9_live_ide_session` stays NOT_RUN until operator runs it)
- No comPREssOR `.py` diffs; HOOK_CONTRACT already documents CC-9 — CC-6 registration documented in checklist (no compressor PR)

Recorded: 2026-09-05 ~13:59 PT (harness UTC in evidence.json).
