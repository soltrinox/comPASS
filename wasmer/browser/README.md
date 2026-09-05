# Browser sandbox

Serve `wasmer/` over HTTP (`file://` cannot fetch the `.wasm` reliably):

```bash
cd wasmer && python3 -m http.server 8765
# open http://127.0.0.1:8765/browser/
```

- Module: `artifacts/compass_core_bg.wasm` (`wasm32-unknown-unknown` cdylib)
- Exports: `compass_alloc`, `compass_free`, `compass_decide_json`, `compass_last_len`, `memory`
- **No** `fetch` import; **no** key material
- Probe remains a native/extension sidecar (not in this page)
- Smoke hooks: `window.__COMPASS_SMOKE__`, `?smoke=1`, `data-smoke-ready`

## Headless smoke (Track J)

```bash
# from wasmer/browser
npm install
npx playwright install chromium
# from repo root
node ../../scripts/wasmer_browser_smoke.mjs
# or with system Chrome:
COMPASS_SMOKE_CHANNEL=chrome node scripts/wasmer_browser_smoke.mjs
```

Evidence: `test-results/j-wasmer-packaging/browser-smoke.json` + `.log.txt`.
CI: `.github/workflows/wasmer-browser.yml`.
