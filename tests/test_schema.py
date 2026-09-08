"""Schema package: load packaged model-graph.v1.json and validate nodes."""

from __future__ import annotations

import hashlib
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

# Canonical schema lives at src/compass/schema/model-graph.v1.json — loader.py reads it
# at runtime and it is the only copy packaged into the sdist/wheel. These two are
# generated mirrors, written by scripts/sync_schema.py and never edited by hand.
MIRROR_RELPATHS = ("schema/model-graph.v1.json", "docs/schema/model-graph.v1.json")


def _repo_root() -> Path | None:
    """Repo checkout root, or None when tests run against an installed distribution."""
    root = Path(__file__).resolve().parents[1]
    return root if (root / "pyproject.toml").is_file() else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def test_canonical_schema_is_the_packaged_copy():
    """The canonical file must stay inside the package so it ships in the wheel."""
    packaged = package_schema_path().resolve()
    assert packaged.parent.name == "schema"
    assert packaged.parent.parent.name == "compass"
    root = _repo_root()
    if root is None:
        pytest.skip("not a repo checkout; canonical path check needs the source tree")
    assert packaged == (root / "src" / "compass" / "schema" / "model-graph.v1.json").resolve()


def test_docs_mirror_matches_package():
    """Repo and docs mirrors must parse equal to the packaged canonical schema."""
    root = _repo_root()
    if root is None:
        pytest.skip("not a repo checkout; mirrors are not packaged")
    packaged = json.loads(package_schema_path().read_text(encoding="utf-8"))
    for relpath in MIRROR_RELPATHS:
        mirror = root / relpath
        assert mirror.is_file(), f"missing mirror {relpath} — run: python scripts/sync_schema.py"
        assert json.loads(mirror.read_text(encoding="utf-8")) == packaged, (
            f"{relpath} differs from canonical — run: python scripts/sync_schema.py"
        )


def test_schema_mirrors_have_no_checksum_drift():
    """Byte-exact guard: all three copies must share one sha256.

    Semantic equality is not enough — reformatting a mirror would silently make the
    three files diverge on disk while still parsing equal, and consumers that pin the
    digest (page-recall manifest, SHA256SUMS) would then disagree with the wheel.
    """
    root = _repo_root()
    if root is None:
        pytest.skip("not a repo checkout; mirrors are not packaged")
    canonical = root / "src" / "compass" / "schema" / "model-graph.v1.json"
    assert canonical.is_file(), "canonical schema missing from src/compass/schema/"
    digests = {"src/compass/schema/model-graph.v1.json": _sha256(canonical)}
    for relpath in MIRROR_RELPATHS:
        mirror = root / relpath
        assert mirror.is_file(), f"missing mirror {relpath} — run: python scripts/sync_schema.py"
        digests[relpath] = _sha256(mirror)
    assert len(set(digests.values())) == 1, (
        "model-graph.v1.json checksum drift — run: python scripts/sync_schema.py\n"
        + "\n".join(f"  {d}  {p}" for p, d in digests.items())
    )


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
