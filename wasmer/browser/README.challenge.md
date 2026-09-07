# Challenge client (Pass+-style)

Entry: `challenge.html` (Docker default `/`).

- `?handle=demo-wasm` or `?binary_url=https://raw.githubusercontent.com/eni6ma/REGISTRY/.../eni6ma_wasm.wasm`
- Digest fail-closed via `circuitLoader.loadPinnedRemote` (+ `/circuit-proxy` for CORS)
- Minimal proof via DEMO-MINT wasm-bindgen pkg
- Ask panel → `agy-bridge` `:8791` with `compass.circuit`

See `docs/DOCKER.md` in the PR.
