# Probe credential rotation runbook

Use this when a Probe key is leaked, aged out, or renamed. Keep Route fail-open throughout — missing Probe credentials must not block Agent Chat.

## Severity classes

| Class | Example | Urgency |
|---|---|---|
| Compromised | Key pasted in chat, committed, or logged | Immediate revoke |
| Routine | 90-day hygiene / provider rotation mail | Schedule within window |
| Rename | Env var rename in a release | Deploy docs + example together |

## Compromise response (immediate)

1. **Revoke** the leaked key at the provider console (OpenRouter / HF / Cursor).
2. **Confirm** it is not in git history for this clone (`git log -p -- .env` should be empty; `.env` is gitignored).
3. **Mint** a replacement key with the same minimum scope; label it `comPASS-probe`.
4. **Update** local env and/or keychain (see below). Do not commit the new value.
5. **Restart** only the Probe sidecar (and Tier-3 proxy if it used a related upstream key). Leave Route/hooks untouched.
6. **Audit** recent Probe logs for unexpected egress; artifacts must stay redacted.
7. If the secret landed in a PR or gist, treat as public: rotate, notify maintainers, scrub if possible.

## Env update

```bash
# Replace values in your untracked .env or shell profile — never in .env.example
export OPENROUTER_API_KEY=...   # new
export HF_TOKEN=...
export CURSOR_API_KEY=...
# Restart Probe process supervisor so it re-reads the environment
```

If an env **name** changes in a release:

1. Update [`.env.example`](../../.env.example) placeholders and [`CREDENTIALS.md`](CREDENTIALS.md).
2. Keep reading the old name for one transition release when safe, or document a hard cut.
3. Operators rename locally; CI must not inject production secrets into WASM jobs.

## Keychain update (macOS)

```bash
security delete-generic-password -s "comPASS.probe" -a "OPENROUTER_API_KEY" 2>/dev/null || true
security add-generic-password -U -s "comPASS.probe" -a "OPENROUTER_API_KEY" -w
# repeat for HF_TOKEN and CURSOR_API_KEY
```

With optional `keyring`:

```python
import keyring
keyring.set_password("comPASS.probe", "OPENROUTER_API_KEY", "<new>")
```

## Proxy upstream keys

If rotating `COMPASS_PROXY_UPSTREAM_API_KEY`, treat it as a **service** secret separate from Probe catalog keys. Restart the proxy process only. Do not write the value into advisory files or Graph snapshots.

## Verification (no secret echo)

```bash
cd comPASS
.venv/bin/python -c "from compass.probe.credentials import audit_credential_presence; print(audit_credential_presence())"
.venv/bin/pytest -q tests/test_credential_boundary.py
```

Expect `present_in_env` / `present_in_keychain` booleans only — never print raw keys.
