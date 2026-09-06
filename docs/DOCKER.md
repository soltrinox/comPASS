# Docker Compose — agy-bridge

Bring up the local **agy-bridge** (ENI6MA Gate → chat completions) without installing Google Antigravity.

**Prerequisite:** Docker Desktop must be running (`docker info` succeeds). On macOS: `open -a Docker`, then wait until the daemon is ready.

## Quick start

```bash
# from repo root
docker compose up --build -d
```

Health check:

```bash
curl -s http://127.0.0.1:8791/healthz
# {"ok":true,"service":"agy-bridge",...}
```

Sample completion (Gate DEV mode; circuit URL+sha256 for cache/fetch):

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

Default compose uses `scripts/fake-agy.js` (`AGY_BIN=/app/scripts/fake-agy.js`) so no live `agy` install is needed. Bind is `0.0.0.0` inside the container (`AGY_BRIDGE_HOST`); host port `8791`.

Circuit WASM cache persists in volume `agy-bridge-circuits` → `/data/circuits`.

## Stop

```bash
docker compose down
```

## Live Antigravity (advanced)

Profile `live-agy` is documented in `docker-compose.yml`. It expects host networking and mounts for the real `agy` binary plus credentials. Default `docker compose up` does **not** require this.

```bash
# after editing mounts in docker-compose.yml
docker compose --profile live-agy up --build -d
```

Local-only default without Docker still binds `127.0.0.1` (`AGY_BRIDGE_HOST` unset).
