# Browser sandbox

Serve `wasmer/` over HTTP (file:// cannot fetch the `.wasm` reliably):

```bash
cd wasmer && python3 -m http.server 8765
# open http://127.0.0.1:8765/browser/
```

- Module: `artifacts/compass_core_bg.wasm` (`wasm32-unknown-unknown` cdylib)
- Exports: `compass_alloc`, `compass_free`, `compass_decide_json`, `compass_last_len`, `memory`
- **No** `fetch` import; **no** key material
- Probe remains a native/extension sidecar (not in this page)
