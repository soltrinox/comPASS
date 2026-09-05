# comPASS Host ABI v1

**ABI version:** `COMPASS_HOST_ABI = 1.0.0`  
**Paired with:** `model-graph/v1`, `compass.core` module (`ABI_MIN`/`ABI_MAX`)  
**Contract refs:** [`docs/STACK.md`](../STACK.md) §3, [`docs/WASMER.md`](../WASMER.md)

## Boundaries (MUST)

| Import | Direction | Allowed | Forbidden |
|---|---|---|---|
| `storage.read_snapshot(agent_or_project_id) -> bytes` | host → module | Graph snapshot, default table, λ, envelopes **without secrets** | Provider keys, raw transcripts policy-forbidden in-browser |
| `clock.now_iso() -> string` | host → module | Timestamps for validity filtering | — |
| `log.write(level, msg)` | module → host | Rationale, errors | Key material, full prompt if policy says no |
| `config.get(key) -> value` | host → module | Non-secret knobs (`default_model_version_id`, `lambda_cost`, `abi_min`) | `*_API_KEY`, tokens |
| `fetch` | optional, **native hosts only** | Not in browser module | Browser build: import **absent** |
| `keys.*` | — | **Does not exist** | Never add |

## Key boundary (security MUST)

- Browser module: **zero** provider keys, **zero** Cursor keys.
- Desktop/mobile module: same. Keys stay in the native Probe/proxy process (OS env / keychain).
- Snapshot producer (native) strips secrets before `storage.read_snapshot`.
- Code review: `rg -i 'api_key|token|secret|authorization' src/compass/core`

## Versioning

- Module advertises `abi_min` / `abi_max` (see `compass.core.abi`).
- Host refuses incompatible modules → fail-open to default endpoint + reason `abi_incompatible`.

## Typed surface

- Python: `compass.core.abi.HostABI` (+ `HostStorage`, `HostClock`, `HostLog`, `HostConfig`)
- Machine-readable: [`host-abi.v1.json`](host-abi.v1.json)

## Forbidden namespaces

`keys` must never appear on the WASM import table. Tests in `tests/test_wasm_boundary.py` enforce that `compass.core` does not import native sidecar packages.
