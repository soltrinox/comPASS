---
name: comPASS Track M — Probe credentials
overview: Real OpenRouter/HF/Cursor credentials behind Probe-only loaders (env/keychain/.env never committed); rotation docs; audit that Route/core/wasm never read secrets.
todos:
  - id: secret-storage-pattern
    content: "Document secret storage pattern — env vars, OS keychain optional, .env never committed; update .env.example"
    status: completed
  - id: probe-only-loaders
    content: "Implement Probe-only credential loaders in src/compass/probe/ (or native/); refuse load outside Probe process boundary"
    status: completed
  - id: provider-docs-openrouter-hf-cursor
    content: "Docs for obtaining/rotating OpenRouter, Hugging Face, and Cursor API credentials for Probe"
    status: completed
  - id: rotation-runbook
    content: "Write rotation runbook (compromise response, env rename, keychain update) under docs/probe/"
    status: completed
  - id: import-boundary-audit
    content: "Automated audit test — Route/core/wasm/serve-hook paths never import secret loaders or os.environ key names for providers"
    status: completed
  - id: proxy-boundary-note
    content: "Clarify Tier-3 proxy may hold upstream keys as a service process — still never in WASM/hooks; document separation from Probe catalog keys"
    status: completed
  - id: proof-m
    content: "Emit test-results/m-credentials/ with audit log (redacted); no real secrets in artifacts"
    status: completed
isProject: true
---

# comPASS Track M — Probe credentials

## Purpose

Enable **real** OpenRouter / Hugging Face / Cursor credentials **only** behind the Probe sidecar (and documented proxy service boundary). Route, Graph read, hooks, and WASM must never see key material.

**Ground truth:** `.env.example`, `tests/test_probe_boundary.py`, `tests/test_wasm_boundary.py`, `docs/INTEGRATION.md`.

**Depends on:** Track I/K soft. **Hard-unblocks** Track F live smoke.

## Locked defaults

- Fail-open Route when credentials missing (no Probe ⇒ use last snapshot / defaults).
- Probe never on prompt path.
- No keys in WASM.
- Never commit `.env` or key files.
- Outcome-equivalence non-claim unchanged.

## Deliverable paths

```
comPASS/
  .env.example
  src/compass/probe/credentials.py      # NEW
  docs/probe/CREDENTIALS.md             # NEW
  docs/probe/ROTATION.md                # NEW
  tests/test_credential_boundary.py     # NEW / extend boundary tests
  test-results/m-credentials/
```

## Acceptance / test criteria

1. Loaders resolve from env (and optional keychain) only when called from Probe entrypoints.
2. Unit test fails the build if `compass.core`, `compass.route`, or wasmer glue import credential module.
3. Docs cover OpenRouter, HF, Cursor obtain + rotate.
4. `git status` / CI secret scan patterns ignore `.env`; example file has empty placeholders only.
5. Proof artifacts are redacted.

## Dependencies

| Unblocks | Track F live transports |
| Soft | Track H live advisory names |

## Explicit non-goals

- Storing user OAuth tokens inside Graph DB.
- Shipping a secrets manager SaaS.
- Putting Cursor auth cookies into the repo or WASM.
