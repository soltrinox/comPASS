# B2 — Browser `@wasmer/sdk` boot (Zone A)

**Date:** 2026-09-07 PT  
**Stage grade:** PARTIAL  
**Why not FULL:** Registry `compass/decide` is unpublished (`wasmer/PUBLISH-NOT_RUN.md`). Zone A boots the **local** `.webc` / `compass_core_bg.wasm`. No fake registry download of `compass/decide`.

## Subgrades

| Check | Grade | Evidence |
|---|---|---|
| CSP (COOP/COEP unchanged; worker-src + blob + Wasmer origins) | FULL | `sdk-boot-*.log.txt` header dump; `evidence.json` `isolated_headers` |
| `window.crossOriginIsolated === true` with COOP/COEP | FULL | isolated page |
| Dynamic import of `@wasmer/sdk` `/browser` entry (`dist/index.js`) | FULL | `sdk.imported` / `sdk.ready` |
| Host `compass_decide_json` vs `wasmer_parity.py` reason codes | FULL | fixture `urn:mg:model:cheap`; missing `snapshot_missing`; corrupt `snapshot_corrupt` |
| Local `.webc` sandbox `compass-decide` | FULL | 258019-byte local package |
| `python/python@=3.13.18` from registry | FULL | stdout `zone-a-python-ok` |
| Fail-open raw instantiate when not isolated | FULL | fallback page `crossOriginIsolated=false`, fixture still green |
| Registry `compass/decide` | NOT_RUN | unpublished; not attempted |

## CSP directive set (document)

```
default-src 'self';
script-src 'self' 'wasm-unsafe-eval' 'unsafe-eval' blob:;
worker-src 'self' blob: 'wasm-unsafe-eval' 'unsafe-eval';
connect-src 'self' http://127.0.0.1:8791 http://localhost:8791 https://raw.githubusercontent.com https://github.com https://objects.githubusercontent.com https://registry.wasmer.io https://cdn.wasmer.io;
img-src 'self' data:;
style-src 'self' 'unsafe-inline';
object-src 'none';
base-uri 'none'
```

COOP `same-origin` / COEP `require-corp` unchanged.

`'unsafe-eval'` is required: `@wasmer/sdk` 0.11.0 wasm-bindgen calls `new Function` (`__wbg_new_with_args`) in WASIX workers. `'wasm-unsafe-eval'` alone produced an `EvalError` (see `sdk-boot-20260907-205015.log.txt`).

Wasmer `connect-src` hosts were verified, not guessed: GraphQL `https://registry.wasmer.io/graphql` is embedded in the SDK wasm; `python/python@=3.13.18` `distribution.downloadUrl` is `https://cdn.wasmer.io/webcimages/…`.

## Docker nginx

`docker-nginx-csp.txt`: COOP/COEP/CSP match the smoke server. Also HTTP 200 for `/healthz`, `/vendor/@wasmer/sdk/dist/index.js`, `/vendor/@wasmer/sdk/pkg/wasmer_sdk_js_bg.wasm`, `/fixtures/snapshot_min.json`, `/artifacts/compass_core_bg.wasm`.

## Re-run

```bash
cd wasmer/browser && npm install && npx playwright install chromium
# from repo root
COMPASS_SMOKE_CHANNEL=chrome node scripts/wasmer_browser_smoke.mjs
COMPASS_ZONEA_PYTHON=1 COMPASS_SMOKE_CHANNEL=chrome node scripts/wasmer_browser_sdk_smoke.mjs
```

Skip the python registry download: `COMPASS_ZONEA_PYTHON=0`.
