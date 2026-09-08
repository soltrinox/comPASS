# Session summary — B2 browser @wasmer/sdk boot (2026-09-07 PT)

**Branch:** `feat/consolidation-and-wasmer`  
**Scope:** Plan todos `b2-csp`, `b2-sdk`, `b2-zonea`.  
**Grade:** PARTIAL (local SDK + compass guest green; registry `compass/decide` NOT_RUN).

## What landed

- nginx CSP in `services/browser-client/nginx.conf`: `worker-src 'self' blob: 'wasm-unsafe-eval' 'unsafe-eval'`; `blob:` and `'unsafe-eval'` on `script-src`; `connect-src` adds `https://registry.wasmer.io` and `https://cdn.wasmer.io`. COOP/COEP unchanged.
- `@wasmer/sdk` **0.11.0** in `wasmer/browser/package.json`. Dynamic import of the `/browser` entry file (`vendor/@wasmer/sdk/dist/index.js`). Guard on `window.crossOriginIsolated`.
- Zone A: local `compass-decide` `.webc` + host `compass_decide_json`; pinned `python/python@=3.13.18` from the registry (stdout `zone-a-python-ok`).
- Fail-open: existing `sandbox.js` raw instantiate when the page is not isolated. Track J smoke stayed FULL.
- Evidence: `test-results/r-browser-sdk/`.

## NOT_RUN

Registry `compass/decide` — unpublished, not attempted.
