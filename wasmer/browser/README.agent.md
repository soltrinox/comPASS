# ENI6MA × comPASS agent stub

Digest-pinned Path-B loader + minimal-proof runner for the browser sandbox.

## Files

| File | Role |
|------|------|
| `circuitLoader.js` | Fetch + SHA-256; fail closed on pin mismatch |
| `wasmerRunner.js` | Load pin → wasm-bindgen `build_minimal_proof` |
| `agent.html` / `agent.js` | Smoke UI |

Pins live in `../artifacts/pins.json`. Published ENI6MA bytes under `../artifacts/eni6ma/demo-wasm/v1/` (Path-B pin); runtime glue in that tree’s `pkg/`.

## Run

```bash
cd wasmer && python3 -m http.server 8765
# http://127.0.0.1:8765/browser/agent.html
```

Gate envelope / burn-before-validate is next; this stub only hardens the digest gate before proof smoke.
