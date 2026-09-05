# Track M — credential boundary proof (redacted)

Date: 2026-09-05 13:13 PT
Repo: soltrinox/comPASS

## Deliverables
- `.env.example` — OPENROUTER_API_KEY / HF_TOKEN / CURSOR_API_KEY placeholders (empty)
- `src/compass/probe/credentials.py` — Probe-only loaders + call-stack refuse
- `docs/probe/CREDENTIALS.md` — obtain + supply via env/keychain
- `docs/probe/ROTATION.md` — compromise / rotate runbook
- `tests/test_credential_boundary.py` — import + loader boundary
- Tier-3 proxy separation noted in CREDENTIALS.md + INTEGRATION.md + .env.example

## Pytest
See pytest.txt (full suite green).

## Audit
See audit-redacted.json (presence booleans only; no secret material).

## Non-goals confirmed
- No live billed API calls in this track
- No real secrets in git
- Route/core/WASM/serve.proxy do not load Probe credential module
