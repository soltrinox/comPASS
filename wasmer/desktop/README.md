# Desktop Wasmer shell (Track J)

Packaged entrypoint beyond raw `.wasm` bytes:

| File | Role |
|---|---|
| `run-decide.sh` | Operator script: volume map, defaults, fail-open demos, exit codes |

The package manifest now lives at the repo root as [`wasmer.toml`](../../wasmer.toml).
It covers both the WASI binary and the browser cdylib in one `compass/decide`
package. Registry publish is NOT_RUN — see [`../PUBLISH-NOT_RUN.md`](../PUBLISH-NOT_RUN.md).

## Run

```bash
# from repo root
./wasmer/desktop/run-decide.sh
# fail-open demos:
COMPASS_FAIL_OPEN_DEMO=missing ./wasmer/desktop/run-decide.sh
COMPASS_FAIL_OPEN_DEMO=corrupt ./wasmer/desktop/run-decide.sh
```

Requires Wasmer CLI on PATH. No provider keys; snapshot is host-supplied JSON only.

## Grade

**PARTIAL → FULL** for desktop packaging when `run-decide.sh` + artifact + parity green.
Mobile device farm remains separate (`wasmer/mobile/NOT_RUN.md`).
