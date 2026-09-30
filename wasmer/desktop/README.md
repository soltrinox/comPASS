# Desktop Wasmer shell (Track J / plan B3)

Packaged entrypoint beyond raw `.wasm` bytes:

| File | Role |
|---|---|
| `run-decide.sh` | Operator script: registry hop (opt-in), local `.webc`, air-gap wasm, volume map, fail-open demos |

The package manifest lives at the repo root as [`wasmer.toml`](../../wasmer.toml).
It covers both the WASI binary and the browser cdylib in one `compass/decide`
package. Registry publish is **NOT_RUN** — see [`../PUBLISH-NOT_RUN.md`](../PUBLISH-NOT_RUN.md).

## Run order

`run-decide.sh` tries hops in this order. Stdout is the decide envelope; hop
diagnostics go to stderr.

1. **Registry by name/version** — only if `COMPASS_WASMER_USE_REGISTRY=1` or
   `--registry`, and a package ref is set (`compass/decide@0.1.0` from the
   manifest, overridable with `COMPASS_WASMER_PACKAGE` / `COMPASS_WASMER_VERSION`
   / `COMPASS_WASMER_REF`). This hop is **code-complete** and **runtime NOT_RUN**
   until a human `wasmer login`, claims namespace `compass`, and
   `wasmer publish .`. Failure is caught and the script falls through.
2. **Local `.webc` (default today)** — `wasmer run --offline` on
   `compass-decide-0.1.0.webc` at the repo root. Built with
   `wasmer package build` if missing.
3. **Air-gap wasm** — `wasmer run --offline wasmer/artifacts/compass-decide.wasm`
   with `--volume "$PWD/wasmer:/wasmer"` (audit §A6 item 11). Same mapping as
   `scripts/wasmer_parity.py`, which still shells `wasmer run` on the raw wasm
   itself.

```bash
# from repo root — default = local .webc
./wasmer/desktop/run-decide.sh
# fail-open demos:
COMPASS_FAIL_OPEN_DEMO=missing ./wasmer/desktop/run-decide.sh
COMPASS_FAIL_OPEN_DEMO=corrupt ./wasmer/desktop/run-decide.sh
# isolate a hop:
COMPASS_DECIDE_SOURCE=webc ./wasmer/desktop/run-decide.sh
COMPASS_DECIDE_SOURCE=wasm ./wasmer/desktop/run-decide.sh
# opt-in registry (expected to fail until PUBLISH-NOT_RUN.md flips):
COMPASS_WASMER_USE_REGISTRY=1 ./wasmer/desktop/run-decide.sh --registry
```

Requires Wasmer CLI on PATH. No provider keys; snapshot is host-supplied JSON only.

## Grade

**PARTIAL** for published-by-name (`wasmer run compass/decide@0.1.0`) — implementation
is in the script; runtime is NOT_RUN. **FULL** for local packaged `.webc` and
loose-artifact fallback when `scripts/wasmer_desktop_packaged.py` and
`scripts/wasmer_parity.py` are green.

Mobile device farm remains separate (`wasmer/mobile/NOT_RUN.md`).
