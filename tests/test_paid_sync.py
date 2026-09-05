"""Track N Pillar 1 — free manual bundle vs paid automated sync."""

from __future__ import annotations

import json

import pytest

from compass.bundle import export_bundle, import_bundle
from compass.graph import GraphStore, GraphStoreConfig, empty_graph
from compass.sync import (
    ENV_PAID_SYNC,
    AutomatedSync,
    PaidFeatureDisabled,
    SyncAutomationConfig,
    export_local_bundle,
    import_local_bundle,
    is_paid_sync_enabled,
    verify_bundle,
)


def _seed_store(root):
    cfg = GraphStoreConfig(root=root)
    with GraphStore(cfg) as store:
        doc = empty_graph()
        doc.nodes.append(
            {
                "id": "urn:mg:model:m1",
                "kind": "ModelVersion",
                "status": "active",
                "valid_start": "2026-09-05T00:00:00Z",
                "valid_end": None,
                "attrs": {"name": "m1"},
            }
        )
        store.save_document(doc)
    return root


def test_manual_local_bundle_round_trip_without_paid_flag(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_PAID_SYNC, raising=False)
    assert is_paid_sync_enabled() is False
    src = _seed_store(tmp_path / "src")
    bundle = tmp_path / "bundle"
    export_local_bundle(src, bundle, agent_id="laptop")
    man = verify_bundle(bundle)
    assert man["schema"] == "bundle/v1"
    assert "graph.json" in man["checksums"]
    dest = tmp_path / "dest"
    import_local_bundle(bundle, dest)
    graph = json.loads((dest / "graph" / "model-graph.json").read_text())
    assert any(n.get("id") == "urn:mg:model:m1" for n in graph["nodes"])


def test_manual_compass_bundle_api_stays_free(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_PAID_SYNC, raising=False)
    src = _seed_store(tmp_path / "src")
    bundle = tmp_path / "bundle"
    export_bundle(str(src), dest=str(bundle), agent_id="free")
    dest = tmp_path / "dest"
    import_bundle(str(bundle), dest=str(dest))
    assert (dest / "graph" / "model-graph.json").exists()


def test_automated_sync_blocked_without_paid_flag(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_PAID_SYNC, raising=False)
    src = _seed_store(tmp_path / "src")
    sync = AutomatedSync(SyncAutomationConfig(enabled=False, fail_open=True))
    result = sync.round_trip(src, tmp_path / "dest")
    assert result.ok is False
    assert result.paid is False
    assert "manual" in (result.reason or "").lower() or "paid" in (result.reason or "").lower()


def test_automated_sync_raises_when_not_fail_open(tmp_path):
    src = _seed_store(tmp_path / "src")
    sync = AutomatedSync(SyncAutomationConfig(enabled=False, fail_open=False))
    with pytest.raises(PaidFeatureDisabled):
        sync.automate_export(src, tmp_path / "b")


def test_automated_round_trip_with_paid_flag(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_PAID_SYNC, "1")
    assert is_paid_sync_enabled() is True
    src = _seed_store(tmp_path / "src")
    dest = tmp_path / "dest"
    sync = AutomatedSync(SyncAutomationConfig(agent_id="workstation"))
    result = sync.round_trip(src, dest, staging_dir=tmp_path / "stage")
    assert result.ok is True
    assert result.paid is True
    graph = json.loads((dest / "graph" / "model-graph.json").read_text())
    assert any(n.get("id") == "urn:mg:model:m1" for n in graph["nodes"])
