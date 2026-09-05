"""Graph store + bitemporal queries + RouteDecision append."""

from __future__ import annotations

from pathlib import Path

from compass.graph import GraphStore, GraphStoreConfig, empty_graph
from compass.schema import SCHEMA_ID, GraphDocument


def test_empty_graph_factory():
    doc = empty_graph()
    assert doc.schema == SCHEMA_ID
    assert doc.nodes == []
    assert doc.edges == []


def test_load_missing_fail_open(tmp_path: Path):
    store = GraphStore(GraphStoreConfig(root=tmp_path / "data"))
    store.open()
    doc = store.load_document(fail_open=True)
    assert doc.nodes == []
    store.close()


def test_load_corrupt_fail_open(tmp_path: Path):
    cfg = GraphStoreConfig(root=tmp_path / "data")
    cfg.graph_dir.mkdir(parents=True)
    cfg.document_path.write_text("{not-json", encoding="utf-8")
    store = GraphStore(cfg)
    store.open()
    doc = store.load_document(fail_open=True)
    assert isinstance(doc, GraphDocument)
    assert doc.nodes == []
    store.close()


def test_save_and_reload_roundtrip(tmp_path: Path):
    cfg = GraphStoreConfig(root=tmp_path / "data")
    store = GraphStore(cfg)
    store.open()
    doc = GraphDocument.from_dict(
        {
            "schema": SCHEMA_ID,
            "nodes": [
                {
                    "id": "urn:mg:modelversion:test",
                    "kind": "ModelVersion",
                    "status": "active",
                    "valid_start": "2026-09-01T00:00:00Z",
                    "valid_end": None,
                    "attrs": {"provider": "test", "model_id": "m1"},
                }
            ],
            "edges": [],
        }
    )
    store.save_document(doc)
    loaded = store.load_document(fail_open=False)
    assert loaded.nodes[0]["id"] == "urn:mg:modelversion:test"
    assert store.active_nodes(kind="ModelVersion")
    store.close()
    assert cfg.meta_db.exists()


def test_active_nodes_filters_status(tmp_path: Path):
    cfg = GraphStoreConfig(root=tmp_path / "data")
    store = GraphStore(cfg)
    with store:
        doc = GraphDocument(
            schema=SCHEMA_ID,
            nodes=[
                {
                    "id": "a",
                    "kind": "ModelVersion",
                    "status": "active",
                    "valid_start": "2026-01-01T00:00:00Z",
                    "valid_end": None,
                },
                {
                    "id": "b",
                    "kind": "ModelVersion",
                    "status": "superseded",
                    "valid_start": "2026-01-01T00:00:00Z",
                    "valid_end": "2026-02-01T00:00:00Z",
                },
            ],
            edges=[],
        )
        store.save_document(doc)
        active = store.active_nodes()
        assert [n["id"] for n in active] == ["a"]


def test_store_validity_and_status_queries(tmp_path: Path):
    cfg = GraphStoreConfig(root=tmp_path / "data")
    with GraphStore(cfg) as store:
        doc = GraphDocument(
            schema=SCHEMA_ID,
            nodes=[
                {
                    "id": "a",
                    "kind": "ModelVersion",
                    "status": "active",
                    "valid_start": "2026-01-01T00:00:00Z",
                    "valid_end": None,
                },
                {
                    "id": "b",
                    "kind": "ModelVersion",
                    "status": "superseded",
                    "valid_start": "2025-01-01T00:00:00Z",
                    "valid_end": "2026-01-01T00:00:00Z",
                },
                {
                    "id": "c",
                    "kind": "ModelVersion",
                    "status": "deprecated",
                    "valid_start": "2026-01-01T00:00:00Z",
                    "valid_end": None,
                },
            ],
            edges=[],
        )
        store.save_document(doc)
        assert [n["id"] for n in store.nodes_by_status("deprecated")] == ["c"]
        at = "2026-06-01T00:00:00Z"
        valid_ids = {n["id"] for n in store.nodes_valid_at(at)}
        assert valid_ids == {"a", "c"}
        assert [n["id"] for n in store.active_nodes(at=at)] == ["a"]


def test_append_route_decision(tmp_path: Path):
    cfg = GraphStoreConfig(root=tmp_path / "data")
    with GraphStore(cfg) as store:
        rid = store.append_route_decision(
            {
                "task_class_id": "code_generation",
                "selected_model_version_id": "m1",
                "scores": {"m1": 0.7},
                "lambda": 1.0,
                "rationale": "test",
                "fail_open": False,
                "default_reason": None,
                "decided_at": "2026-09-05T00:00:00Z",
            },
            decision_id="urn:mg:routedecision:test1",
            at="2026-09-05T00:00:00Z",
        )
        assert rid == "urn:mg:routedecision:test1"
        doc = store.load_document(fail_open=False)
        nodes = [n for n in doc.nodes if n["kind"] == "RouteDecision"]
        assert len(nodes) == 1
        assert nodes[0]["attrs"]["selected_model_version_id"] == "m1"
        edges = [e for e in doc.edges if e["kind"] == "selected"]
        assert len(edges) == 1
        assert edges[0]["to"] == "m1"


def test_read_p95_fixture_graph_cheap(tmp_path: Path):
    """Optional cheap p95 read benchmark on a small fixture graph."""
    import time

    cfg = GraphStoreConfig(root=tmp_path / "data")
    nodes = []
    for i in range(200):
        nodes.append(
            {
                "id": f"urn:mg:modelversion:{i}",
                "kind": "ModelVersion",
                "status": "active" if i % 5 else "superseded",
                "valid_start": "2026-01-01T00:00:00Z",
                "valid_end": None if i % 5 else "2026-02-01T00:00:00Z",
                "attrs": {"i": i},
            }
        )
    with GraphStore(cfg) as store:
        store.save_document(GraphDocument(schema=SCHEMA_ID, nodes=nodes, edges=[]))
        samples = []
        for _ in range(30):
            t0 = time.perf_counter()
            _ = store.active_nodes(kind="ModelVersion")
            samples.append((time.perf_counter() - t0) * 1000.0)
        samples.sort()
        p95 = samples[int(0.95 * (len(samples) - 1))]
        # Soft bound: tens of ms on a tiny fixture (CI machines vary)
        assert p95 < 50.0, f"p95 read {p95:.2f}ms exceeded 50ms soft target"
