"""Load and lightly validate model-graph/v1 documents.

Full JSON-Schema validation is optional; this module enforces the
contract fields Route/Graph need without requiring jsonschema at runtime.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

SCHEMA_ID = "model-graph/v1"

NODE_KINDS = frozenset(
    {
        "Provider",
        "Model",
        "ModelVersion",
        "TaskClass",
        "CapabilityAxis",
        "Probe",
        "Observation",
        "PriceQuote",
        "Policy",
        "RouteDecision",
    }
)

EDGE_KINDS = frozenset(
    {
        "serves",
        "version_of",
        "measures",
        "observed_on",
        "evidences",
        "priced_by",
        "supersedes",
        "derived_from",
        "constrains",
        "selected",
    }
)

STATUS_VALUES = frozenset({"active", "superseded", "deprecated"})


class SchemaError(ValueError):
    """Raised when a model-graph document or node violates the v1 contract."""


def package_schema_path() -> Path:
    """Return the filesystem path to the packaged model-graph.v1.json."""
    ref = resources.files("compass.schema").joinpath("model-graph.v1.json")
    with resources.as_file(ref) as path:
        return Path(str(path))


def load_schema_path() -> dict[str, Any]:
    """Load the JSON Schema document shipped with the package."""
    ref = resources.files("compass.schema").joinpath("model-graph.v1.json")
    return json.loads(ref.read_text(encoding="utf-8"))


def _require_keys(obj: dict[str, Any], keys: tuple[str, ...], label: str) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise SchemaError(f"{label} missing required keys: {missing}")


@dataclass
class GraphDocument:
    """In-memory model-graph/v1 document with light validation."""

    schema: str = SCHEMA_ID
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphDocument:
        if not isinstance(data, dict):
            raise SchemaError("graph document must be an object")
        _require_keys(data, ("schema", "nodes", "edges"), "graph")
        if data["schema"] != SCHEMA_ID:
            raise SchemaError(f"unsupported schema id: {data['schema']!r}")
        if not isinstance(data["nodes"], list) or not isinstance(data["edges"], list):
            raise SchemaError("nodes and edges must be arrays")
        doc = cls(
            schema=data["schema"],
            nodes=deepcopy(data["nodes"]),
            edges=deepcopy(data["edges"]),
        )
        doc.validate()
        return doc

    @classmethod
    def load(cls, path: str | Path) -> GraphDocument:
        raw = Path(path).read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SchemaError(f"corrupt JSON: {exc}") from exc
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "nodes": deepcopy(self.nodes),
            "edges": deepcopy(self.edges),
        }

    def save(self, path: str | Path) -> None:
        self.validate()
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + chr(10), encoding="utf-8")

    def validate(self) -> None:
        if self.schema != SCHEMA_ID:
            raise SchemaError(f"unsupported schema id: {self.schema!r}")
        for node in self.nodes:
            self._validate_node(node)
        for edge in self.edges:
            self._validate_edge(edge)

    @staticmethod
    def _validate_node(node: dict[str, Any]) -> None:
        if not isinstance(node, dict):
            raise SchemaError("node must be an object")
        _require_keys(node, ("id", "kind", "status", "valid_start", "valid_end"), "node")
        if node["kind"] not in NODE_KINDS:
            raise SchemaError(f"invalid node kind: {node['kind']!r}")
        if node["status"] not in STATUS_VALUES:
            raise SchemaError(f"invalid node status: {node['status']!r}")

    @staticmethod
    def _validate_edge(edge: dict[str, Any]) -> None:
        if not isinstance(edge, dict):
            raise SchemaError("edge must be an object")
        _require_keys(
            edge,
            ("id", "kind", "from", "to", "status", "valid_start", "valid_end"),
            "edge",
        )
        if edge["kind"] not in EDGE_KINDS:
            raise SchemaError(f"invalid edge kind: {edge['kind']!r}")
        if edge["status"] not in STATUS_VALUES:
            raise SchemaError(f"invalid edge status: {edge['status']!r}")


    def node_by_id(self, node_id: str) -> dict[str, Any] | None:
        """Return the first node with the given id, or None."""
        for node in self.nodes:
            if node.get("id") == node_id:
                return node
        return None

    def supersede(
        self,
        old_id: str,
        new_node: dict[str, Any],
        *,
        at: str | None = None,
        reason: str = "superseded",
        new_id: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Close ``old_id`` validity and open ``new_node`` with a supersedes edge.

        Mirrors compressor CtxGraph.supersede semantics (not its enums):
        set old status=superseded, close valid_end, insert new as active,
        add edge kind=supersedes from new → old. Prior observations stay
        attached to the superseded version.
        """
        from copy import deepcopy as _deepcopy

        old = self.node_by_id(old_id)
        if old is None:
            raise SchemaError(f"supersede target not found: {old_id!r}")
        stamp = at or _now_iso()
        new = _deepcopy(new_node)
        if new_id is not None:
            new["id"] = new_id
        if "id" not in new or not new["id"]:
            raise SchemaError("new_node must include a non-empty id")
        if new["id"] == old_id:
            raise SchemaError("new node id must differ from superseded id")
        if self.node_by_id(new["id"]) is not None:
            raise SchemaError(f"new node id already exists: {new['id']!r}")
        if "kind" not in new:
            # Default: same kind as superseded node (ModelVersion drift case)
            new["kind"] = old.get("kind")
        _require_keys(new, ("id", "kind"), "new_node")

        # Close old interval
        old["status"] = "superseded"
        old["valid_end"] = stamp
        attrs = old.setdefault("attrs", {})
        if isinstance(attrs, dict):
            attrs["supersede_reason"] = reason

        # Open new interval (fill bitemporal fields before validate)
        if not new.get("valid_start"):
            new["valid_start"] = stamp
        new["status"] = "active"
        if "valid_end" not in new:
            new["valid_end"] = None
        self._validate_node(new)
        self.nodes.append(new)

        edge = {
            "id": f"urn:mg:edge:supersedes:{new['id']}:{old_id}",
            "kind": "supersedes",
            "from": new["id"],
            "to": old_id,
            "status": "active",
            "valid_start": stamp,
            "valid_end": None,
            "attrs": {"reason": reason},
        }
        self._validate_edge(edge)
        self.edges.append(edge)
        return old, new, edge

    def nodes_by_status(
        self,
        status: str,
        *,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        """Filter nodes by status (active / superseded / deprecated)."""
        if status not in STATUS_VALUES:
            raise SchemaError(f"invalid status filter: {status!r}")
        out = [n for n in self.nodes if n.get("status") == status]
        if kind is not None:
            out = [n for n in out if n.get("kind") == kind]
        return out

    def nodes_valid_at(
        self,
        at: str,
        *,
        kind: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Nodes whose validity interval contains ``at`` (valid_start ≤ at < valid_end|∞)."""
        out: list[dict[str, Any]] = []
        for node in self.nodes:
            if not _interval_contains(node.get("valid_start"), node.get("valid_end"), at):
                continue
            if status is not None and node.get("status") != status:
                continue
            if kind is not None and node.get("kind") != kind:
                continue
            out.append(node)
        return out

    def deprecated_nodes(self, *, kind: str | None = None) -> list[dict[str, Any]]:
        return self.nodes_by_status("deprecated", kind=kind)

    def superseded_nodes(self, *, kind: str | None = None) -> list[dict[str, Any]]:
        return self.nodes_by_status("superseded", kind=kind)

    def active_nodes(self, *, kind: str | None = None, at: str | None = None) -> list[dict[str, Any]]:
        """Active nodes; when ``at`` is set, also require validity containing ``at``."""
        if at is None:
            return self.nodes_by_status("active", kind=kind)
        return self.nodes_valid_at(at, kind=kind, status="active")


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _interval_contains(valid_start: Any, valid_end: Any, at: str) -> bool:
    """True when valid_start <= at and (valid_end is None or at < valid_end)."""
    if not isinstance(valid_start, str) or not valid_start:
        return False
    if at < valid_start:
        return False
    if valid_end is None:
        return True
    if not isinstance(valid_end, str):
        return False
    return at < valid_end
