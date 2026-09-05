"""Schema package: load packaged model-graph.v1.json and validate nodes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compass.schema import (
    NODE_KINDS,
    SCHEMA_ID,
    GraphDocument,
    SchemaError,
    load_schema_path,
    package_schema_path,
)


def test_package_schema_exists_and_loads():
    path = package_schema_path()
    assert path.exists()
    schema = load_schema_path()
    assert schema["title"] == "model-graph/v1"
    assert "ModelVersion" in schema["$defs"]["node"]["properties"]["kind"]["enum"]


def test_example_model_version_validates():
    schema = load_schema_path()
    example = schema["examples"][0]
    doc = GraphDocument.from_dict(example)
    assert doc.schema == SCHEMA_ID
    assert doc.nodes[0]["kind"] == "ModelVersion"


def test_invalid_node_kind_raises():
    with pytest.raises(SchemaError, match="invalid node kind"):
        GraphDocument.from_dict(
            {
                "schema": SCHEMA_ID,
                "nodes": [
                    {
                        "id": "x",
                        "kind": "NotAKind",
                        "status": "active",
                        "valid_start": "2026-01-01T00:00:00Z",
                        "valid_end": None,
                    }
                ],
                "edges": [],
            }
        )


def test_node_kinds_match_contract():
    assert "RouteDecision" in NODE_KINDS
    assert "TaskClass" in NODE_KINDS


def test_docs_mirror_matches_package(tmp_path: Path):
    """Repo docs/schema and packaged schema should stay in sync when both present."""
    packaged = json.loads(package_schema_path().read_text(encoding="utf-8"))
    docs = Path("docs/schema/model-graph.v1.json")
    repo = Path("schema/model-graph.v1.json")
    for mirror in (docs, repo):
        if mirror.exists():
            assert json.loads(mirror.read_text(encoding="utf-8")) == packaged


def test_supersede_closes_old_opens_new():
    doc = GraphDocument(
        schema=SCHEMA_ID,
        nodes=[
            {
                "id": "urn:mg:modelversion:old",
                "kind": "ModelVersion",
                "status": "active",
                "valid_start": "2026-01-01T00:00:00Z",
                "valid_end": None,
                "attrs": {"capability": {"code_generation": {"mean": 0.5, "n": 10, "ci95": 0.1}}},
            }
        ],
        edges=[],
    )
    old, new, edge = doc.supersede(
        "urn:mg:modelversion:old",
        {
            "id": "urn:mg:modelversion:new",
            "kind": "ModelVersion",
            "attrs": {"drift_fingerprint": "cn_new"},
        },
        at="2026-09-01T12:00:00Z",
        reason="fingerprint_shift",
    )
    assert old["status"] == "superseded"
    assert old["valid_end"] == "2026-09-01T12:00:00Z"
    assert old["attrs"]["supersede_reason"] == "fingerprint_shift"
    assert new["status"] == "active"
    assert new["valid_start"] == "2026-09-01T12:00:00Z"
    assert new["valid_end"] is None
    assert edge["kind"] == "supersedes"
    assert edge["from"] == new["id"]
    assert edge["to"] == old["id"]
    # Prior capability attrs remain on the superseded node (not overwritten)
    assert old["attrs"]["capability"]["code_generation"]["mean"] == 0.5


def test_bitemporal_status_and_validity_queries():
    doc = GraphDocument(
        schema=SCHEMA_ID,
        nodes=[
            {
                "id": "active-open",
                "kind": "ModelVersion",
                "status": "active",
                "valid_start": "2026-01-01T00:00:00Z",
                "valid_end": None,
            },
            {
                "id": "superseded-closed",
                "kind": "ModelVersion",
                "status": "superseded",
                "valid_start": "2025-01-01T00:00:00Z",
                "valid_end": "2026-01-01T00:00:00Z",
            },
            {
                "id": "deprecated-open",
                "kind": "ModelVersion",
                "status": "deprecated",
                "valid_start": "2026-01-01T00:00:00Z",
                "valid_end": None,
            },
            {
                "id": "active-future",
                "kind": "ModelVersion",
                "status": "active",
                "valid_start": "2026-12-01T00:00:00Z",
                "valid_end": None,
            },
        ],
        edges=[],
    )
    assert [n["id"] for n in doc.nodes_by_status("active")] == ["active-open", "active-future"]
    assert [n["id"] for n in doc.superseded_nodes()] == ["superseded-closed"]
    assert [n["id"] for n in doc.deprecated_nodes()] == ["deprecated-open"]
    at = "2026-06-01T00:00:00Z"
    valid = doc.nodes_valid_at(at)
    ids = {n["id"] for n in valid}
    assert "active-open" in ids
    assert "deprecated-open" in ids
    assert "superseded-closed" not in ids  # ended at 2026-01-01
    assert "active-future" not in ids  # not yet started
    active_at = doc.active_nodes(at=at)
    assert [n["id"] for n in active_at] == ["active-open"]


def test_supersede_unknown_raises():
    doc = GraphDocument(schema=SCHEMA_ID, nodes=[], edges=[])
    with pytest.raises(SchemaError, match="not found"):
        doc.supersede("missing", {"id": "n", "kind": "ModelVersion"})
