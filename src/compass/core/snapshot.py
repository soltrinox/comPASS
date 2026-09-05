"""Immutable graph snapshot view for the Route read path.

Snapshots are pre-serialized by the native host (Probe/sidecar) and fed through
``HostABI.storage_read_snapshot``. No filesystem, no SQLite, no secrets.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from compass.core.defaults import SNAPSHOT_CORRUPT, SNAPSHOT_MISSING


@dataclass(frozen=True)
class GraphSnapshot:
    """Immutable in-memory view of a model-graph/v1 (or lite) document."""

    schema: str = "model-graph/v1"
    nodes: tuple[dict[str, Any], ...] = ()
    edges: tuple[dict[str, Any], ...] = ()
    meta: dict[str, Any] = field(default_factory=dict)
    ok: bool = True
    error_code: str | None = None

    def active_model_versions(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for n in self.nodes:
            if n.get("kind") != "ModelVersion":
                continue
            if n.get("status", "active") != "active":
                continue
            out.append(dict(n))
        return out

    def candidates_from_nodes(self) -> list[dict[str, Any]]:
        """Map ModelVersion nodes → decide() candidate dicts (id/quality/cost)."""
        cands: list[dict[str, Any]] = []
        for n in self.active_model_versions():
            attrs = n.get("attrs") or {}
            mid = str(n.get("id") or "")
            if not mid:
                continue
            cands.append(
                {
                    "id": mid,
                    "model_version_id": mid,
                    "quality": float(attrs.get("quality", attrs.get("expected_quality", 0.5))),
                    "cost": float(attrs.get("cost", attrs.get("expected_cost", 1.0))),
                }
            )
        return cands


def parse_snapshot(raw: bytes | str | dict[str, Any] | None) -> GraphSnapshot:
    """Parse host-provided bytes/JSON into an immutable snapshot.

    Missing → ok=False + snapshot_missing; corrupt → snapshot_corrupt.
    Never raises into the decide hot path.
    """
    if raw is None:
        return GraphSnapshot(ok=False, error_code=SNAPSHOT_MISSING.code)
    if isinstance(raw, dict):
        data = raw
    elif isinstance(raw, str):
        if not raw.strip():
            return GraphSnapshot(ok=False, error_code=SNAPSHOT_MISSING.code)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return GraphSnapshot(ok=False, error_code=SNAPSHOT_CORRUPT.code)
    elif isinstance(raw, (bytes, bytearray)):
        if not raw:
            return GraphSnapshot(ok=False, error_code=SNAPSHOT_MISSING.code)
        try:
            text = bytes(raw).decode("utf-8")
        except UnicodeError:
            return GraphSnapshot(ok=False, error_code=SNAPSHOT_CORRUPT.code)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return GraphSnapshot(ok=False, error_code=SNAPSHOT_CORRUPT.code)
    else:
        return GraphSnapshot(ok=False, error_code=SNAPSHOT_CORRUPT.code)
    if not isinstance(data, dict):
        return GraphSnapshot(ok=False, error_code=SNAPSHOT_CORRUPT.code)
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return GraphSnapshot(ok=False, error_code=SNAPSHOT_CORRUPT.code)
    schema = str(data.get("schema", "model-graph/v1"))
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    # Shallow-copy nodes/edges so callers cannot mutate our tuples' dicts via shared refs
    # after we freeze the container; dict values remain mutable by Python semantics —
    # treat as read-only by convention in WASM hosts.
    return GraphSnapshot(
        schema=schema,
        nodes=tuple(dict(n) if isinstance(n, dict) else {} for n in nodes),
        edges=tuple(dict(e) if isinstance(e, dict) else {} for e in edges),
        meta=dict(meta),
        ok=True,
        error_code=None,
    )
