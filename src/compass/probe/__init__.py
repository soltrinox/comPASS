"""Probe plane — native sidecar (offline fixtures + env-gated live HTTP).

Credential boundary (normative)
--------------------------------
* Provider API keys are **never** imported, read, or held by ``compass.route``
  or ``compass.graph`` (or compressor hooks / browser WASM).
* Only the Probe process is allowed to hold provider credentials — via
  ``compass.probe.credentials`` (Track M).
* Route and hook code must not import ``compass.probe.runner``,
  ``compass.probe.credentials``, ``compass.probe.network_gate``, or
  ``compass.probe.live_transports``.
* Network egress defaults **OFF** (``COMPASS_PROBE_ALLOW_NETWORK`` unset/false).
* Route/decide must never block on Probe HTTP (fail-open).

See ``docs/ARCHITECTURE.md`` §1, ``docs/probe/LIVE-SMOKE.md``, and ``.env.example``.
"""

from __future__ import annotations

__all__ = [
    "sample_tasks",
    "load_corpus",
    "run_probe",
    "network_allowed",
    "run_canaries",
    "apply_fingerprint_shift",
    "persist_observation",
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
    if name == "persist_observation":
        from compass.probe import observations as _obs

        return getattr(_obs, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
