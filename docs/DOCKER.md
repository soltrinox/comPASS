# Docker Compose — agy-bridge + browser challenge client

Bring up the local **agy-bridge** (ENI6MA Gate → chat completions) and the **browser challenge client** (Pass+-style handle / binary URL → digest-pin → prove → ask).

**Prerequisite:** Docker Desktop must be running (`docker info` succeeds). On macOS: `open -a Docker`, then wait until the daemon is ready.

## Quick start

```bash
# from repo root
docker compose up --build -d
```

| Surface | URL |
|---------|-----|
| **Challenge UI** | http://127.0.0.1:8088/ |
| agy-bridge health | http://127.0.0.1:8791/healthz |
| browser-client health | http://127.0.0.1:8088/healthz |

### Challenge entry (like Pass+ / `circuit.eni6ma.com/passplus`)

- Handle: http://127.0.0.1:8088/challenge.html?handle=demo-wasm
- Binary URL: http://127.0.0.1:8088/challenge.html?binary_url=https://raw.githubusercontent.com/eni6ma/REGISTRY/feat/wasm-circuits/circuits/demo-wasm/v1/eni6ma_wasm.wasm&sha256=853717e421a36fc93d0791d3f2718ecf3e9c449fb3c60d4084dedab3af75c389
- Or click **Use local pin** to load `wasmer/artifacts` digest without GitHub.

Flow: first paint is the challenge form → **Load & Prove** fetches via same-origin `/circuit-proxy` (allowlisted GitHub hosts) → SHA-256 fail-closed → DEMO-MINT `build_minimal_proof` in-tab → **Ask / execute** posts to `:8791` with `compass.circuit`.

Sample completion (Gate DEV mode):

```bash
curl -s http://127.0.0.1:8791/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "agy",
    "messages": [{ "role": "user", "content": "reply with exactly: pong" }],
    "compass": {
      "circuit": {
        "url": "https://raw.githubusercontent.com/eni6ma/REGISTRY/feat/wasm-circuits/circuits/demo-wasm/v1/eni6ma_wasm.wasm",
        "sha256": "853717e421a36fc93d0791d3f2718ecf3e9c449fb3c60d4084dedab3af75c389",
        "proof": { "stub": true }
      }
    }
  }'
```

Default compose uses `scripts/fake-agy.js` so no live `agy` install is needed.

## Stop

```bash
docker compose down
```

## Live Antigravity (advanced)

Profile `live-agy` is documented in `docker-compose.yml`. Default `docker compose up` does **not** require it.
