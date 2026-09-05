"""Drift detection helpers that trigger ModelVersion supersession.

Fingerprint shift beyond threshold → supersede via GraphDocument (Probe canary
calls into this path), never overwrite scores across a break.

Credential boundary: this Graph-adjacent helper never reads provider keys.
"""

from __future__ import annotations


def fingerprint_changed(previous: str | None, current: str | None, *, threshold: float = 0.0) -> bool:
    """Return True when canary fingerprint indicates a break.

    Offline skeleton: any non-equal non-empty pair is a change. ``threshold``
    is reserved for calibrated distance metrics later.
    """
    _ = threshold
    if not previous or not current:
        return False
    return previous != current
