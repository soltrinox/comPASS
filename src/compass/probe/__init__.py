"""Probe plane — native sidecar daemon skeleton (offline).

Credential boundary (normative)
--------------------------------
* Provider API keys are **never** imported, read, or held by ``compass.route``
  or ``compass.graph`` (or compressor hooks / browser WASM).
* Only the Probe process is allowed to hold provider credentials — and only
  when live probing is explicitly enabled later. This offline skeleton does
  **not** load keys and does **not** make provider HTTP calls.
* Route and hook code must not import ``compass.probe.runner``.
* Network egress defaults **OFF** (``COMPASS_PROBE_ALLOW_NETWORK`` unset/false).

See ``docs/ARCHITECTURE.md`` §1 and repo ``.env.example``.
"""

from __future__ import annotations

__all__ = [
    "sample_tasks",
    "load_corpus",
    "run_probe",
    "network_allowed",
    "run_canaries",
    "apply_fingerprint_shift",
]


def __getattr__(name: str):
    # Lazy exports so importing compass.probe alone does not pull runner into
    # unexpected graphs; explicit submodule imports remain the boundary test.
    if name in {"sample_tasks", "load_corpus"}:
        from compass.probe import corpus as _corpus

        return getattr(_corpus, name)
    if name in {"run_probe", "network_allowed"}:
        from compass.probe import runner as _runner

        return getattr(_runner, name)
    if name in {"run_canaries", "apply_fingerprint_shift"}:
        from compass.probe import canary as _canary

        return getattr(_canary, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
