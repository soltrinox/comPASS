"""Canary drift set against active ModelVersions (offline skeleton).

Not bandit-pruned. Fingerprint shift → supersede ModelVersion via GraphDocument
(never overwrite scores across a break). Unit tests inject mock fingerprints;
no network calls here.
"""

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from compass.schema import GraphDocument
from compass.score.drift import fingerprint_changed

CANARY_ENV = "COMPASS_PROBE_CANARY_SET"
FingerprintFn = Callable[[str, Mapping[str, Any]], str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_canary_path() -> Path:
    override = os.environ.get(CANARY_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return _repo_root() / "fixtures" / "probe" / "canary_set.json"


def load_canary_set(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Load the fixed canary prompt set from repo fixtures."""
    p = Path(path) if path is not None else default_canary_path()
    if not p.is_file():
        raise FileNotFoundError(f"canary set not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    canaries = data.get("canaries") if isinstance(data, dict) else None
    if not isinstance(canaries, list) or not canaries:
        raise ValueError("canary set must include a non-empty canaries list")
    return list(canaries)


def mock_fingerprint(model_version_id: str, canary: Mapping[str, Any]) -> str:
    """Deterministic offline fingerprint (no network)."""
    cid = canary.get("id", "")
    prompt = canary.get("prompt", "")
    material = f"{model_version_id}|{cid}|{prompt}"
    return "fp_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def compose_version_fingerprint(
    model_version_id: str,
    canaries: list[Mapping[str, Any]],
    *,
    get_fingerprint: FingerprintFn | None = None,
) -> str:
    """Combine per-canary fingerprints into one ModelVersion fingerprint."""
    fn = get_fingerprint or mock_fingerprint
    parts = [fn(model_version_id, c) for c in canaries]
    joined = "|".join(parts)
    return "cn_" + hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]


@dataclass
class CanaryResult:
    model_version_id: str
    previous_fingerprint: str | None
    current_fingerprint: str
    changed: bool
    superseded: bool
    new_model_version_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_version_id": self.model_version_id,
            "previous_fingerprint": self.previous_fingerprint,
            "current_fingerprint": self.current_fingerprint,
            "changed": self.changed,
            "superseded": self.superseded,
            "new_model_version_id": self.new_model_version_id,
        }


def apply_fingerprint_shift(
    doc: GraphDocument,
    old_id: str,
    *,
    new_fingerprint: str,
    at: str | None = None,
    new_id: str | None = None,
    reason: str = "fingerprint_shift",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Call GraphDocument.supersede for a canary-detected fingerprint break.

    Prior observations remain attached to the superseded ModelVersion.
    """
    old = doc.node_by_id(old_id)
    if old is None:
        raise KeyError(f"ModelVersion not found: {old_id!r}")
    stamp_id = new_id or f"{old_id}:drift:{new_fingerprint}"
    prior_attrs = deepcopy(old.get("attrs") or {})
    # Do not carry measured capability posteriors across the break.
    prior_attrs.pop("capability", None)
    prior_attrs["drift_fingerprint"] = new_fingerprint
    prior_attrs["supersedes_prior"] = old_id
    new_node = {
        "id": stamp_id,
        "kind": "ModelVersion",
        "attrs": prior_attrs,
    }
    return doc.supersede(old_id, new_node, at=at, reason=reason)


def run_canaries(
    doc: GraphDocument,
    *,
    model_version_ids: list[str] | None = None,
    canaries: list[dict[str, Any]] | None = None,
    get_fingerprint: FingerprintFn | None = None,
    threshold: float = 0.0,
    at: str | None = None,
    apply_supersede: bool = True,
) -> list[dict[str, Any]]:
    """Run the fixed canary set against active ModelVersions (mockable).

    When a fingerprint changes beyond threshold, optionally call into the
    graph supersede path. Never performs network I/O; inject ``get_fingerprint``
    for tests / future live transport.
    """
    canary_list = canaries if canaries is not None else load_canary_set()
    if model_version_ids is None:
        active = doc.active_nodes(kind="ModelVersion")
        model_version_ids = [str(n["id"]) for n in active]

    results: list[CanaryResult] = []
    for mv_id in model_version_ids:
        node = doc.node_by_id(mv_id)
        previous = None
        if node is not None:
            previous = (node.get("attrs") or {}).get("drift_fingerprint")
            if previous is not None:
                previous = str(previous)
        current = compose_version_fingerprint(
            mv_id, canary_list, get_fingerprint=get_fingerprint
        )
        changed = fingerprint_changed(previous, current, threshold=threshold)
        # First observation: establish baseline without superseding.
        if previous is None:
            if node is not None:
                attrs = node.setdefault("attrs", {})
                if isinstance(attrs, dict):
                    attrs["drift_fingerprint"] = current
            results.append(
                CanaryResult(
                    model_version_id=mv_id,
                    previous_fingerprint=None,
                    current_fingerprint=current,
                    changed=False,
                    superseded=False,
                )
            )
            continue

        superseded = False
        new_id = None
        if changed and apply_supersede and node is not None:
            _old, new, _edge = apply_fingerprint_shift(
                doc, mv_id, new_fingerprint=current, at=at
            )
            superseded = True
            new_id = str(new["id"])
        results.append(
            CanaryResult(
                model_version_id=mv_id,
                previous_fingerprint=previous,
                current_fingerprint=current,
                changed=changed,
                superseded=superseded,
                new_model_version_id=new_id,
            )
        )
    return [r.to_dict() for r in results]
