# DEMO-MINT circuit WASM ABI notes

**Artifact:** `eni6ma_wasm.wasm` (DEMO-MINT / demo-wasm v1)  
**URL:** https://raw.githubusercontent.com/eni6ma/REGISTRY/feat/wasm-circuits/circuits/demo-wasm/v1/eni6ma_wasm.wasm  
**SHA-256:** `853717e421a36fc93d0791d3f2718ecf3e9c449fb3c60d4084dedab3af75c389`  
**Size:** 600779 bytes (~586.7 KiB)  
**Inspected:** 2026-09-06 (PT) via `WebAssembly.Module.exports` / `wasmer inspect`

## Summary

This is a **wasm-bindgen** (Rust→WASM) module, not a freestanding verify/challenge ABI.

| Category | Finding |
|---|---|
| Toolchain | `__wbindgen_*` describe exports + `__wbindgen_placeholder__` / `__wbindgen_externref_xform__` imports |
| Semantic export | **`build_minimal_proof`** (function) — prove/mint oriented |
| Verify / challenge | **None** found as named freestanding exports (`verify`, `challenge`, `prove`, `validate`, …) |
| Memory | Exported `memory` |
| Instantiate (empty imports) | **Fails** — requires wbindgen host imports |
| Node Gate today | Digest pin + compile + ABI probe; real proof verify deferred until JS glue or a verify-shaped export exists |

## Meaningful exports (non-`__wbindgen_describe_*`)

| Name | Kind | Notes |
|---|---|---|
| `memory` | memory | Linear memory |
| `build_minimal_proof` | function | Primary semantic entry (wasm-bindgen signature; needs glue) |
| `__externref_table_alloc` | function | wbindgen runtime |
| `__externref_table_dealloc` | function | wbindgen runtime |
| `__externref_drop_slice` | function | wbindgen runtime |
| `__abort_handler` | global | runtime |
| `__instance_terminated` | global | runtime |
| `__data_end` | global | linker |
| `__heap_base` | global | linker |

Total exports reported by `WebAssembly.Module.exports`: **1384** (vast majority are `__wbindgen_describe_*` metadata stubs).

## Imports (12)

**Module `__wbindgen_placeholder__`:**

- `__wbg_set_8a16b38e4805b298`
- `__wbindgen_object_drop_ref`
- `__wbindgen_describe`
- `__wbindgen_describe_cast`
- `__wbg_String_8564e559799eccda`
- `__wbindgen_object_clone_ref`
- `__wbg_set_6be42768c690e380`
- `__wbg_new_da52cf8fe3429cb2`
- `__wbg_new_32b398fb48b6d94a`
- `__wbg___wbindgen_throw_344f42d3211c4765`

**Module `__wbindgen_externref_xform__`:**

- `__wbindgen_externref_table_grow`
- `__wbindgen_externref_table_set_null`

## Gate implications (`eni6maValidate`)

1. **Always** fail closed on SHA-256 mismatch (client pin and/or sidecar).
2. **Compile** the module; **probe** exports/imports and classify ABI (`abi_probe`).
3. Detect known names (`build_minimal_proof`, future `verify*` / `challenge*`). Today: **prove-oriented, opaque for Node without glue**.
4. Soft-instantiate with stub wbindgen imports when possible (load OK); calling `build_minimal_proof` without official glue is **not** treated as proof verification.
5. Modes:
   - `digest_ok` / `abi_probe` — digest + compile + export inventory
   - `digest_only` — when `AGY_GATE_DEV=1` after compile/soft-instantiate (proof optional)
   - `proof_required` — when `AGY_GATE_STRICT=1` and proof/challenge missing or empty
   - Future: wire real verify when a verify-shaped export or JS glue is available

## Registry note

See REGISTRY `circuits/demo-wasm/v1/README.snippet.md`: fetch WASM + `.sha256` sidecar; recompute digest; match or fail closed before instantiate. Cohort zip may embed `private.json` (sensitive); prefer isolated WASM + digest.
