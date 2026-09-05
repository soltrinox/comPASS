"""Graph plane: bitemporal capability store (SQLite metadata + JSON docs).

C2: supersede + validity queries live on GraphDocument; GraphStore adds
RouteDecision append helpers and fail-open reads. Writes are intended for
Probe (and RouteDecision persistence from decide); Route primarily reads.
No provider keys are stored or accepted here.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from compass.schema.loader import SCHEMA_ID, GraphDocument, SchemaError


@dataclass
class GraphStoreConfig:
    """Paths for the two-tier store. Operator-configurable; no machine paths baked in."""

    root: Path
    default_document_name: str = "model-graph.json"
    bandit_document_name: str = "bandit-posterior.json"

    @property
    def meta_db(self) -> Path:
        return self.root / "meta.sqlite"

    @property
    def graph_dir(self) -> Path:
        return self.root / "graph"

    @property
    def document_path(self) -> Path:
        return self.graph_dir / self.default_document_name

    @property
    def bandit_path(self) -> Path:
        return self.graph_dir / self.bandit_document_name


class GraphStore:
    """SQLite indexes + JSON document store for model-graph/v1.

    Fail-open: corrupt or missing documents yield an empty GraphDocument
    rather than raising into the Route hot path.
    """

    def __init__(self, config: GraphStoreConfig) -> None:
        self.config = config
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        self.config.root.mkdir(parents=True, exist_ok=True)
        self.config.graph_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.config.meta_db)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                name TEXT PRIMARY KEY,
                updated_at REAL NOT NULL,
                bytes INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> GraphStore:
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def load_document(self, *, fail_open: bool = True) -> GraphDocument:
        """Load the primary graph document.

        When fail_open is True (default), missing/corrupt JSON returns an
        empty document instead of raising.
        """
        path = self.config.document_path
        if not path.exists():
            if fail_open:
                return empty_graph()
            raise FileNotFoundError(path)
        try:
            return GraphDocument.load(path)
        except (SchemaError, OSError, UnicodeError):
            if fail_open:
                return empty_graph()
            raise

    def save_document(self, doc: GraphDocument) -> None:
        """Persist a validated document and refresh SQLite metadata."""
        if self._conn is None:
            self.open()
        assert self._conn is not None
        doc.validate()
        self.config.graph_dir.mkdir(parents=True, exist_ok=True)
        path = self.config.document_path
        path.write_text(json.dumps(doc.to_dict(), indent=2) + chr(10), encoding="utf-8")
        self._conn.execute(
            """
            INSERT INTO documents(name, updated_at, bytes)
            VALUES(?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
              updated_at=excluded.updated_at,
              bytes=excluded.bytes
            """,
            (self.config.default_document_name, time.time(), path.stat().st_size),
        )
        self._conn.commit()

    def active_nodes(
        self,
        kind: str | None = None,
        *,
        at: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return active nodes from a fail-open document load.

        When ``at`` is provided, also require the validity interval to contain ``at``.
        """
        doc = self.load_document(fail_open=True)
        return doc.active_nodes(kind=kind, at=at)

    def nodes_by_status(self, status: str, *, kind: str | None = None) -> list[dict[str, Any]]:
        doc = self.load_document(fail_open=True)
        try:
            return doc.nodes_by_status(status, kind=kind)
        except SchemaError:
            return []

    def nodes_valid_at(
        self,
        at: str,
        *,
        kind: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        doc = self.load_document(fail_open=True)
        return doc.nodes_valid_at(at, kind=kind, status=status)

    def append_route_decision(
        self,
        attrs: dict[str, Any],
        *,
        decision_id: str | None = None,
        at: str | None = None,
        selected_edge: bool = True,
    ) -> str:
        """Append a RouteDecision node (and optional selected edge) and save.

        Fail-open callers should wrap this; persistence errors must not block
        returning a routing choice to the user.
        """
        from datetime import datetime, timezone

        stamp = at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rid = decision_id or f"urn:mg:routedecision:{uuid.uuid4().hex[:12]}"
        doc = self.load_document(fail_open=True)
        node = {
            "id": rid,
            "kind": "RouteDecision",
            "status": "active",
            "valid_start": stamp,
            "valid_end": None,
            "attrs": dict(attrs),
        }
        doc.nodes.append(node)
        selected = attrs.get("selected_model_version_id")
        if selected_edge and selected:
            edge = {
                "id": f"urn:mg:edge:selected:{rid}",
                "kind": "selected",
                "from": rid,
                "to": str(selected),
                "status": "active",
                "valid_start": stamp,
                "valid_end": None,
                "attrs": {},
            }
            doc.edges.append(edge)
        self.save_document(doc)
        return rid



    def find_route_decisions(
        self,
        *,
        trajectory_id: str | None = None,
        episode_id: str | None = None,
        route_decision_id: str | None = None,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Return RouteDecision nodes matching attribution join keys (fail-open)."""
        nodes = (
            self.active_nodes(kind="RouteDecision")
            if active_only
            else [n for n in self.load_document(fail_open=True).nodes if n.get("kind") == "RouteDecision"]
        )
        out: list[dict[str, Any]] = []
        for n in nodes:
            if route_decision_id and n.get("id") == route_decision_id:
                out.append(n)
                continue
            attrs = n.get("attrs") if isinstance(n.get("attrs"), dict) else {}
            if trajectory_id and attrs.get("trajectory_id") == trajectory_id:
                out.append(n)
                continue
            if episode_id and attrs.get("episode_id") == episode_id:
                out.append(n)
                continue
        return out

    def attribute_delayed_reward(
        self,
        reward: Any,
        *,
        policy: str = "trajectory",
        at: str | None = None,
        posterior: Any | None = None,
        update_bandit: bool | None = None,
    ) -> Any:
        """Post-hoc delayed reward join (Track G). Never call from decide()."""
        from compass.score.attribution import DelayedReward, attach_delayed_reward

        if not isinstance(reward, DelayedReward):
            reward = DelayedReward(
                value=float(getattr(reward, "value", reward["value"])),
                source=str(getattr(reward, "source", "verifiable")),
                trajectory_id=getattr(reward, "trajectory_id", None),
                episode_id=getattr(reward, "episode_id", None),
                route_decision_id=getattr(reward, "route_decision_id", None),
                task_class_id=getattr(reward, "task_class_id", None),
                observed_at=str(getattr(reward, "observed_at", "") or ""),
            )
        return attach_delayed_reward(
            self,
            reward,
            policy=policy,  # type: ignore[arg-type]
            at=at,
            posterior=posterior,
            update_bandit=update_bandit,
        )


def empty_graph() -> GraphDocument:
    """Factory for the fail-open empty graph."""
    return GraphDocument(schema=SCHEMA_ID, nodes=[], edges=[])
