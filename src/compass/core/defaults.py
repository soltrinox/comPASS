"""Fail-open default table for Route decide (WASM + native parity).

Reason codes are stable strings shared by native core and future WASM builds.
Divergence from this table is a release blocker (Track D fail-open parity).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class FailOpenReason:
    """Machine-readable fail-open reason + human rationale prefix."""

    code: str
    rationale: str


# Normative codes (docs/WASMER.md § Fail-open parity).
SNAPSHOT_MISSING: Final = FailOpenReason("snapshot_missing", "fail-open: snapshot_missing")
SNAPSHOT_CORRUPT: Final = FailOpenReason("snapshot_corrupt", "fail-open: snapshot_corrupt")
MODULE_TRAP: Final = FailOpenReason("module_trap", "fail-open: module_trap")
NO_CANDIDATES: Final = FailOpenReason("no_candidates", "fail-open: no_candidates")
ABI_INCOMPATIBLE: Final = FailOpenReason("abi_incompatible", "fail-open: abi_incompatible")

FAIL_OPEN_DEFAULTS: Final[dict[str, FailOpenReason]] = {
    SNAPSHOT_MISSING.code: SNAPSHOT_MISSING,
    SNAPSHOT_CORRUPT.code: SNAPSHOT_CORRUPT,
    MODULE_TRAP.code: MODULE_TRAP,
    NO_CANDIDATES.code: NO_CANDIDATES,
    ABI_INCOMPATIBLE.code: ABI_INCOMPATIBLE,
}

# Default endpoint id when graph/decide cannot choose (operator overrides via config).
DEFAULT_MODEL_VERSION_ID: Final[str] = "default"
DEFAULT_QUALITY: Final[float] = 0.5
DEFAULT_COST: Final[float] = 1.0
DEFAULT_LAMBDA: Final[float] = 1.0
