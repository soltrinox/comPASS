# Live Probe smoke (env-gated)

**Default grade: NOT_RUN.** Live HTTP is off unless you explicitly enable it.

## Dry-run (always safe)

```bash
cd comPASS
# network stays OFF
unset COMPASS_PROBE_ALLOW_NETWORK   # or =0
.venv/bin/pytest -q tests/test_probe_network_gate.py tests/test_probe_live_transports_mocked.py
```

Mocked transports cover HF / OpenRouter / Cursor catalog + canary success / 4xx / timeout without sockets.

## Optional live smoke (PARTIAL / FULL)

Requires **all** of:

1. `COMPASS_PROBE_ALLOW_NETWORK=1`
2. Host on allowlist
3. At least one of `OPENROUTER_API_KEY` / `HF_TOKEN` / `CURSOR_API_KEY` present (via env or keychain)
4. Operator has read [TERMS-CHECKLIST.md](TERMS-CHECKLIST.md)

```bash
export COMPASS_PROBE_ALLOW_NETWORK=1
export OPENROUTER_API_KEY=...   # or HF_TOKEN / CURSOR_API_KEY
.venv/bin/python - <<'PY'
from compass.probe.live_transports import fetch_live_catalog
from compass.probe.credentials import credential_presence
print(credential_presence("openrouter").to_audit_dict())
# Catalog only — keep fan-out tiny; rate limiter budget applies
r = fetch_live_catalog("openrouter")
print(r.to_dict())
PY
```

### Grading

| Grade | Meaning |
|---|---|
| **NOT_RUN** | Network off and/or keys absent (CI default; committed evidence below) |
| **PARTIAL** | One provider catalog or canary succeeded under the gate |
| **FULL** | HF + OpenRouter + Cursor catalog paths each succeeded once |

Committed CI artifacts under `test-results/f-live-probe/` record **NOT_RUN** unless an operator re-runs with keys.

## Route isolation

Route/decide must **never** await Probe HTTP. Import audits in
`tests/test_probe_boundary.py`, `tests/test_credential_boundary.py`, and
`tests/test_probe_live_transports_mocked.py` prove `compass.route` /
`compass.core` do not reference `network_gate`, live transports, or credential loaders.
