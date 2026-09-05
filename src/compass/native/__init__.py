"""Native-only sidecar surface (excluded from WASM builds).

Track D / STACK.md: Probe, ingest, and proxy-with-credentials stay **native**.
Existing packages remain importable at their Track C paths for the Python
engine; this package documents the exclusion boundary for Wasmer packaging.

WASM-forbidden import roots (must not appear in ``compass.core`` import graph):

- ``compass.probe``
- ``compass.ingest``
- ``compass.serve`` (proxy / advisory that may touch owned call sites)
- any future ``compass.native.keys`` (must never exist)

Pairing: native sidecar writes a sanitized snapshot; WASM core reads via host ABI;
sidecar executes provider HTTP with keys from OS env/keychain — never inside WASM.
"""

from __future__ import annotations

# Re-export markers for packaging / import-linter configs (lazy-safe names only).
NATIVE_PACKAGES: tuple[str, ...] = (
    "compass.probe",
    "compass.ingest",
    "compass.serve",
)

__all__ = ["NATIVE_PACKAGES"]
