"""WASM-safe Route + Graph **read** core (Track D).

This package is the boundary for Wasmer / browser builds:
classify, score-from-snapshot, decide, immutable snapshot view, fail-open defaults.

**Never** import probe, ingest, serve/proxy, or any provider-key module from here.
Host I/O only via ``compass.core.abi.HostABI`` (storage read / clock / log / config).
See ``docs/WASMER.md`` and ``docs/abi/host-abi.v1.md``.
"""

from __future__ import annotations

from compass.core.classify import classify
from compass.core.decide import decide_from_snapshot
from compass.core.defaults import FAIL_OPEN_DEFAULTS, FailOpenReason
from compass.core.snapshot import GraphSnapshot, parse_snapshot
from compass.core.score_read import score_candidates

__all__ = [
    "FAIL_OPEN_DEFAULTS",
    "FailOpenReason",
    "GraphSnapshot",
    "classify",
    "decide_from_snapshot",
    "parse_snapshot",
    "score_candidates",
]

# Semantic version of the *module* surface (paired with host ABI + model-graph/v1).
CORE_MODULE_VERSION = "0.1.0"
ABI_MIN = "1.0.0"
ABI_MAX = "1.999.0"
