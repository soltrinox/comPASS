# agy-bridge

Thin local Express microservice bridging OpenAI chat to Google Antigravity CLI.

## Air-gap
agy must be installed and authenticated locally. No provider keys in Express.
Binds 127.0.0.1 only.

## Env
AGY_BIN default agy; AGY_BRIDGE_PORT default 8791; AGY_EXTRA_ARGS optional; AGY_TIMEOUT_MS default 300000; AGY_FAIL_OPEN default 1.

## Endpoints
GET /healthz
POST /v1/chat/completions (strips compass; last user message to agy print mode)

## Gate
gateEni6maDigestCheck stub always passes (ADR 0007 TODO).

## Setup

Directory: services/agy-bridge. Install deps with the Node package manager, then start via package.json script "start". Do not commit node_modules.
Default URL: http://127.0.0.1:8791

## HTTP smoke

1) GET http://127.0.0.1:8791/healthz
2) POST http://127.0.0.1:8791/v1/chat/completions with JSON {model, messages, optional compass}.
Last user message is forwarded to agy print mode.

## Security

No provider API keys in this process. Optional AGY_EXTRA_ARGS may include --sandbox.

## Exact curl examples

```text
curl -sS http://127.0.0.1:8791/healthz

curl -sS http://127.0.0.1:8791/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"model":"agy","messages":[{"role":"user","content":"reply with exactly: pong"}],"compass":{"selection_mode":"proxy_override"}}'
```

Smoke result (2026-09-06 PT): healthz 200; completions 200 with choices[0].message.content = pong (agy invoke succeeded; no auth blocker).
