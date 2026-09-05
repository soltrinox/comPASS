# Probe credentials — OpenRouter / Hugging Face / Cursor

**Audience:** operators enabling gated live Probe (Track F).  
**Rule:** secrets stay in the **Probe sidecar** (and optionally the Tier-3 **proxy service**). Route, Graph read, compressor hooks, and browser WASM never see key material.

Related: [`ROTATION.md`](ROTATION.md), [`.env.example`](../../.env.example), [`../INTEGRATION.md`](../INTEGRATION.md) §3, [`../STACK.md`](../STACK.md).

## What belongs where

| Secret | Process | Env var(s) | Keychain account (service `comPASS.probe`) |
|---|---|---|---|
| OpenRouter API key | Probe only | `OPENROUTER_API_KEY` | `OPENROUTER_API_KEY` |
| Hugging Face Hub token | Probe only | `HF_TOKEN` (alt: `HUGGING_FACE_HUB_TOKEN`) | `HF_TOKEN` |
| Cursor API key (model list / Observatory) | Probe only | `CURSOR_API_KEY` | `CURSOR_API_KEY` |
| Upstream OpenAI-compatible key | Tier-3 **proxy service** only | `COMPASS_PROXY_UPSTREAM_API_KEY` (optional) | n/a — not Probe catalog |

Probe catalog keys and proxy upstream keys are **different boundaries**. Do not load Probe loaders from `compass.serve.proxy`.

## Never commit

* Do not commit `.env`, key files, or shell history dumps with secrets.
* `.env.example` must keep **empty placeholders** only.
* Proof artifacts under `test-results/` must be **redacted** (presence booleans only).

## How to supply keys locally

### 1. Environment (simplest)

```bash
cp .env.example .env   # gitignored
# edit .env with real values — never commit
export $(grep -v '^#' .env | xargs)   # or use direnv
```

Or export in the Probe process supervisor only:

```bash
export OPENROUTER_API_KEY=...   # real value stays local
export HF_TOKEN=...
export CURSOR_API_KEY=...
```

### 2. OS keychain (optional)

macOS example (service name must match loaders):

```bash
security add-generic-password -U -s "comPASS.probe" -a "OPENROUTER_API_KEY" -w
security add-generic-password -U -s "comPASS.probe" -a "HF_TOKEN" -w
security add-generic-password -U -s "comPASS.probe" -a "CURSOR_API_KEY" -w
```

Optional Python [`keyring`](https://pypi.org/project/keyring/) package uses the same service/account labels when installed; it is **not** a hard dependency of `compass-router`.

### 3. Loaders

```python
from compass.probe.credentials import (
    load_openrouter_api_key,
    load_huggingface_token,
    load_cursor_api_key,
    audit_credential_presence,
)

# Probe entrypoints only — Route/core/proxy callers raise CredentialBoundaryError
key = load_openrouter_api_key()  # str | None
print(audit_credential_presence())  # redacted presence rows
```

Missing credentials ⇒ Probe stays dry-run / fail-open Route uses last snapshot. Never block Agent Chat.

## Obtaining credentials

### OpenRouter

1. Create an account at [openrouter.ai](https://openrouter.ai/).
2. Open Keys → create a key with the minimum scope needed for catalog + chat probes.
3. Store as `OPENROUTER_API_KEY` (env or keychain). Prefer a dedicated key labeled `comPASS-probe`.

### Hugging Face

1. Create a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
2. Read access to public model cards is enough for priors; do not request write unless required.
3. Store as `HF_TOKEN` (Hub also accepts `HUGGING_FACE_HUB_TOKEN`).

### Cursor

1. Use a Cursor API / dashboard credential intended for **server-side** model-list or Observatory use — not IDE session cookies.
2. Store as `CURSOR_API_KEY`.
3. Never paste Cursor auth cookies into the repo, WASM, or Graph DB.

## Fail-open & network gate

* `COMPASS_PROBE_ALLOW_NETWORK` defaults **OFF**. Live transports require an explicit truthy value.
* Absent keys: Probe must not crash Route; use mock/dry-run or last Graph snapshot.
* Outcome-equivalence non-claim unchanged ([`../CHARTER.md`](../CHARTER.md)).

## Proxy separation (Tier 3)

The local OpenAI-compatible proxy (`python -m compass.serve.proxy`) may forward to an upstream and may hold `COMPASS_PROXY_UPSTREAM` / `COMPASS_PROXY_UPSTREAM_API_KEY` in the **service process**. That is enforcement wiring, not Probe catalog ingestion. Hooks and WASM still never hold those keys.
