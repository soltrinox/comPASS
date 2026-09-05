# Desktop Wasmer shell (Track J)

Packaged entrypoint beyond raw `.wasm` bytes:

| File | Role |
|---|---|
| `run-decide.sh` | Operator script: volume map, defaults, fail-open demos, exit codes |
| `wasmer.toml` | Wasmer package manifest pointing at `../artifacts/compass-decide.wasm` |

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
