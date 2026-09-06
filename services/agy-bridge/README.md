# agy-bridge

Thin local Express microservice bridging OpenAI chat to Google Antigravity CLI (`agy`), with an **ENI6MA circuit Gate** in front of every completion.

## Air-gap

`agy` must be installed and authenticated locally. No provider keys in Express.
Binds `127.0.0.1` only.

## Env

| Variable | Default | Meaning |
|---|---|---|
| `AGY_BIN` | `agy` | CLI binary |
| `AGY_BRIDGE_PORT` | `8791` | Listen port |
| `AGY_EXTRA_ARGS` | _(empty)_ | Extra args after `--print <prompt>` |
| `AGY_TIMEOUT_MS` | `300000` | Spawn timeout |
| `AGY_FAIL_OPEN` | `1` | On agy CLI failure return 200 stub; also enables Gate `digest_ok` + ABI probe when proof missing |
| `AGY_GATE_DEV` | _(unset)_ | `1` allow missing proof after digest + compile/soft-instantiate (`mode: digest_only`) |
| `AGY_GATE_STRICT` | _(unset)_ | `1` reject missing/empty proof (`mode: proof_required`) |
| `AGY_GATE_REQUIRED` | _(unset)_ | `1` reject requests with no `circuit` |
| `COMPASS_CIRCUIT_CACHE` | `~/.compass/circuits/` | WASM cache dir (files named by sha256 hex) |

## Endpoints

- `GET /healthz`
- `POST /v1/chat/completions` — Gate then last user message to `agy --print`

## Circuit request shape

Pass under `compass.circuit` (preferred) or top-level `circuit`:

```json
{
  "model": "agy",
  "messages": [{ "role": "user", "content": "reply with exactly: pong" }],
  "compass": {
    "circuit": {
      "url": "https://raw.githubusercontent.com/eni6ma/REGISTRY/feat/wasm-circuits/circuits/demo-wasm/v1/eni6ma_wasm.wasm",
      "sha256": "853717e421a36fc93d0791d3f2718ecf3e9c449fb3c60d4084dedab3af75c389",
      "proof": { "stub": true },
      "challenge_id": "optional-challenge"
    }
  }
}
```

| Field | Required | Notes |
|---|---|---|
| `url` | on cache miss | HTTPS only; allowlisted hosts only |
| `sha256` | preferred pin | 64 hex; mismatch → HTTP 403 fail closed |
| `proof` / `challenge_id` | unless DEV / fail-open | Opaque DEMO-MINT has no freestanding verify; see ABI doc |

### Gate flow

1. Resolve: cache by sha256, url index, or allowlisted fetch (+ optional sidecar).
2. Recompute digest; mismatch → 403, never call agy.
3. `eni6maValidate`: `WebAssembly.compile` + ABI probe (exports/imports) + soft-instantiate.
4. Modes: `digest_ok` / `abi_probe` (records exports); `digest_only` when `AGY_GATE_DEV=1`; `proof_required` when `AGY_GATE_STRICT=1` and proof missing.
5. On pass → agy --print; response `compass.gate` meta (may include trimmed `abi`).
6. Strip compass/circuit from CLI path.

See ADR `docs/adr/0007-agy-behind-eni6ma-gate.md` and **`docs/CIRCUIT-ABI.md`** (DEMO-MINT export inventory).

### DEMO-MINT ABI (short)

- wasm-bindgen module; semantic export **`build_minimal_proof`**
- No `verify` / `challenge` freestanding exports today
- Empty-import instantiate fails; Gate soft-instantiates with stub wbindgen imports for load OK
- Full notes: [`docs/CIRCUIT-ABI.md`](docs/CIRCUIT-ABI.md)

## Setup

Default URL http://127.0.0.1:8791

## Smoke

Run node scripts/unit-gate.js then start the server and node scripts/smoke-gate.js

## Security

No provider API keys. Allowlist fetch; digest fail-closed.

See docs/client-example.json for an adapter override + circuit body.
