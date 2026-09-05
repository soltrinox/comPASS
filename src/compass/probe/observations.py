"""Persist Observation nodes into the Graph store.

Observations carry capability figures ``{mean, n, ci95}``. Canary / probe
fingerprint changes supersede the prior Observation (bitemporal), never
overwrite scores in place. ToS fleet-redistribute gates apply on write.
"""

from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping

from compass.probe.tos_policy import gate_observation_payload
from compass.schema import GraphDocument
from compass.schema.loader import SchemaError

try:
    from compass.graph import GraphStore
except ImportError:  # pragma: no cover
    GraphStore = None  # type: ignore


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def capability_figure(
    mean: float,
    n: int,
    ci95: float | None = None,
) -> dict[str, float | int]:
    """Build a schema-shaped capability figure."""
    if ci95 is None:
        # Conservative wide interval when n is tiny.
        ci95 = 1.0 if n <= 0 else max(0.05, 1.96 * (0.25 / (n ** 0.5)))
    return {"mean": float(mean), "n": int(n), "ci95": float(ci95)}


def observation_fingerprint(attrs: Mapping[str, Any]) -> str:
    """Stable fingerprint over probe identity + response digest fields."""
    material = "|".join(
        [
            str(attrs.get("probe_id") or ""),
            str(attrs.get("model_version_id") or attrs.get("observed_on") or ""),
            str(attrs.get("task_class") or ""),
            str(attrs.get("response_fingerprint") or ""),
            str(attrs.get("provider") or ""),
        ]
    )
    return "ob_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def build_observation_node(
    *,
    probe_id: str,
    model_version_id: str,
    quality: Mapping[str, Any] | None = None,
    cost: Mapping[str, Any] | None = None,
    provider: str | None = None,
    task_class: str | None = None,
    response_fingerprint: str | None = None,
    fleet_redistribute: bool = False,
    comparative: bool = False,
    extra_attrs: Mapping[str, Any] | None = None,
    at: str | None = None,
    observation_id: str | None = None,
) -> dict[str, Any]:
    """Construct a bitemporal Observation node (not yet attached to a doc)."""
    stamp = at or _now_iso()
    q = dict(quality or capability_figure(0.5, 0))
    c = dict(cost or capability_figure(0.0, 0, 0.0))
    for fig in (q, c):
        if not all(k in fig for k in ("mean", "n", "ci95")):
            raise ValueError("quality/cost must include {mean, n, ci95}")
    attrs: dict[str, Any] = {
        "probe_id": probe_id,
        "model_version_id": model_version_id,
        "observed_on": model_version_id,
        "provider": provider,
        "task_class": task_class,
        "quality": q,
        "cost": c,
        "response_fingerprint": response_fingerprint,
        "fleet_redistribute": fleet_redistribute,
        "comparative": comparative,
    }
    if extra_attrs:
        attrs.update(dict(extra_attrs))
    attrs = gate_observation_payload(attrs)
    attrs["observation_fingerprint"] = observation_fingerprint(attrs)
    oid = observation_id or (
        f"urn:mg:observation:{hashlib.sha256(attrs['observation_fingerprint'].encode()).hexdigest()[:12]}"
    )
    return {
        "id": oid,
        "kind": "Observation",
        "status": "active",
        "valid_start": stamp,
        "valid_end": None,
        "attrs": attrs,
    }


def _find_active_observation(
    doc: GraphDocument,
    *,
    probe_id: str,
    model_version_id: str,
) -> dict[str, Any] | None:
    for node in doc.active_nodes(kind="Observation"):
        attrs = node.get("attrs") or {}
        if attrs.get("probe_id") == probe_id and (
            attrs.get("model_version_id") == model_version_id
            or attrs.get("observed_on") == model_version_id
        ):
            return node
    return None


def persist_observation(
    doc: GraphDocument,
    observation: Mapping[str, Any] | None = None,
    *,
    probe_id: str | None = None,
    model_version_id: str | None = None,
    quality: Mapping[str, Any] | None = None,
    cost: Mapping[str, Any] | None = None,
    provider: str | None = None,
    task_class: str | None = None,
    response_fingerprint: str | None = None,
    fleet_redistribute: bool = False,
    comparative: bool = False,
    extra_attrs: Mapping[str, Any] | None = None,
    at: str | None = None,
    supersede_on_fingerprint_change: bool = True,
) -> dict[str, Any]:
    """Append (or supersede) an Observation on ``doc`` and return the active node.

    When an active Observation exists for the same (probe_id, model_version_id)
    and the fingerprint changed, supersede rather than overwrite.
    """
    stamp = at or _now_iso()
    if observation is None:
        if not probe_id or not model_version_id:
            raise ValueError("probe_id and model_version_id required when observation is omitted")
        node = build_observation_node(
            probe_id=probe_id,
            model_version_id=model_version_id,
            quality=quality,
            cost=cost,
            provider=provider,
            task_class=task_class,
            response_fingerprint=response_fingerprint,
            fleet_redistribute=fleet_redistribute,
            comparative=comparative,
            extra_attrs=extra_attrs,
            at=stamp,
        )
    else:
        node = deepcopy(dict(observation))
        if node.get("kind") != "Observation":
            raise SchemaError("persist_observation expects kind=Observation")
        attrs = gate_observation_payload(dict(node.get("attrs") or {}))
        attrs["observation_fingerprint"] = observation_fingerprint(attrs)
        node["attrs"] = attrs
        node.setdefault("status", "active")
        node.setdefault("valid_start", stamp)
        node.setdefault("valid_end", None)

    attrs = node["attrs"]
    pid = str(attrs.get("probe_id") or "")
    mvid = str(attrs.get("model_version_id") or attrs.get("observed_on") or "")
    new_fp = str(attrs.get("observation_fingerprint") or "")

    prior = _find_active_observation(doc, probe_id=pid, model_version_id=mvid) if pid and mvid else None
    if prior is not None and supersede_on_fingerprint_change:
        old_fp = str((prior.get("attrs") or {}).get("observation_fingerprint") or "")
        if old_fp and old_fp != new_fp:
            # Ensure new id differs
            if node["id"] == prior["id"]:
                node["id"] = f"{prior['id']}:fp:{new_fp[-8:]}"
            old, new, _edge = doc.supersede(
                prior["id"],
                node,
                at=stamp,
                reason="observation_fingerprint_change",
            )
            # Attach observed_on edge if missing
            _ensure_observed_on(doc, new["id"], mvid, at=stamp)
            return new
        if old_fp == new_fp:
            # Idempotent: return existing
            return prior

    # Fresh insert
    if doc.node_by_id(node["id"]) is not None:
        node["id"] = f"{node['id']}:{stamp.replace(':', '')}"
    doc._validate_node(node)  # noqa: SLF001 — shared contract helper
    doc.nodes.append(node)
    _ensure_observed_on(doc, node["id"], mvid, at=stamp)
    return node


def _ensure_observed_on(doc: GraphDocument, obs_id: str, model_version_id: str, *, at: str) -> None:
    if not model_version_id:
        return
    for edge in doc.edges:
        if (
            edge.get("kind") == "observed_on"
            and edge.get("from") == obs_id
            and edge.get("to") == model_version_id
            and edge.get("status") == "active"
        ):
            return
    edge = {
        "id": f"urn:mg:edge:observed_on:{obs_id}",
        "kind": "observed_on",
        "from": obs_id,
        "to": model_version_id,
        "status": "active",
        "valid_start": at,
        "valid_end": None,
        "attrs": {},
    }
    doc._validate_edge(edge)  # noqa: SLF001
    doc.edges.append(edge)


def persist_observation_to_store(
    store: "GraphStore",
    **kwargs: Any,
) -> dict[str, Any]:
    """Load → persist Observation → save. Probe-side only."""
    doc = store.load_document(fail_open=True)
    node = persist_observation(doc, **kwargs)
    store.save_document(doc)
    return node


__all__ = [
    "build_observation_node",
    "capability_figure",
    "observation_fingerprint",
    "persist_observation",
    "persist_observation_to_store",
]
