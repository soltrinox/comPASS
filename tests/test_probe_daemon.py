"""Probe daemon offline skeleton: corpus, runner gate, canary supersede, boundary."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from compass.probe.canary import (
    apply_fingerprint_shift,
    load_canary_set,
    run_canaries,
)
from compass.probe.corpus import load_corpus, sample_tasks
from compass.probe.runner import (
    NETWORK_ENV,
    ProbeNetworkDisabledError,
    network_allowed,
    run_probe,
)
from compass.schema import SCHEMA_ID, GraphDocument
from compass.score.drift import fingerprint_changed


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_CORPUS = REPO_ROOT / "fixtures" / "probe" / "corpus.json"
FIXTURE_CANARY = REPO_ROOT / "fixtures" / "probe" / "canary_set.json"


def test_corpus_loads_synthetic_fixtures():
    data = load_corpus(FIXTURE_CORPUS)
    assert data["schema"] == "compass-probe-corpus/v1"
    tasks = sample_tasks(2, path=FIXTURE_CORPUS)
    assert len(tasks) == 2
    assert all("prompt" in t and "id" in t for t in tasks)
    assert all(t.get("attrs", {}).get("synthetic") for t in sample_tasks(10, path=FIXTURE_CORPUS))


def test_corpus_default_path_resolves_repo_fixtures():
    tasks = sample_tasks(1)
    assert tasks and tasks[0]["id"].startswith("urn:mg:probe-task:")


def test_runner_dry_run_returns_mock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(NETWORK_ENV, raising=False)
    result = run_probe("urn:mg:probe:test", task={"prompt": "hi", "task_class": "code_generation"})
    assert result.mock is True
    assert result.network_used is False
    assert result.observation["kind"] == "Observation"
    assert result.observation["attrs"]["mock"] is True
    assert network_allowed() is False


def test_runner_refuses_live_when_network_env_off(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(NETWORK_ENV, raising=False)
    with pytest.raises(ProbeNetworkDisabledError, match="defaults OFF"):
        run_probe("urn:mg:probe:live", mode="live")


def test_runner_live_requires_task_fields_when_env_on(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(NETWORK_ENV, "1")
    assert network_allowed() is True
    with pytest.raises(ValueError, match="provider"):
        run_probe("urn:mg:probe:live", mode="live")


def test_fingerprint_changed_helper():
    assert fingerprint_changed("a", "b") is True
    assert fingerprint_changed("a", "a") is False
    assert fingerprint_changed(None, "a") is False


def test_canary_fingerprint_change_supersedes_not_overwrite():
    old_id = "urn:mg:modelversion:canary-target"
    doc = GraphDocument(
        schema=SCHEMA_ID,
        nodes=[
            {
                "id": old_id,
                "kind": "ModelVersion",
                "status": "active",
                "valid_start": "2026-01-01T00:00:00Z",
                "valid_end": None,
                "attrs": {
                    "provider": "fixture",
                    "model_id": "m-canary",
                    "drift_fingerprint": "cn_baseline",
                    "capability": {
                        "code_generation": {"mean": 0.82, "n": 40, "ci95": 0.05}
                    },
                },
            },
            {
                "id": "urn:mg:observation:prior",
                "kind": "Observation",
                "status": "active",
                "valid_start": "2026-02-01T00:00:00Z",
                "valid_end": None,
                "attrs": {"observed_on": old_id, "quality": {"mean": 0.82, "n": 40, "ci95": 0.05}},
            },
        ],
        edges=[
            {
                "id": "urn:mg:edge:observed:prior",
                "kind": "observed_on",
                "from": "urn:mg:observation:prior",
                "to": old_id,
                "status": "active",
                "valid_start": "2026-02-01T00:00:00Z",
                "valid_end": None,
                "attrs": {},
            }
        ],
    )

    canaries = load_canary_set(FIXTURE_CANARY)

    def shifted_fp(model_version_id: str, canary: dict) -> str:
        return "shifted|" + model_version_id + "|" + str(canary["id"])

    results = run_canaries(
        doc,
        model_version_ids=[old_id],
        canaries=canaries,
        get_fingerprint=shifted_fp,
        at="2026-09-05T07:00:00Z",
    )
    assert len(results) == 1
    assert results[0]["changed"] is True
    assert results[0]["superseded"] is True
    assert results[0]["new_model_version_id"]

    old = doc.node_by_id(old_id)
    assert old is not None
    assert old["status"] == "superseded"
    assert old["valid_end"] == "2026-09-05T07:00:00Z"
    # Prior capability scores remain on the superseded node (not overwritten away).
    assert old["attrs"]["capability"]["code_generation"]["mean"] == 0.82

    new = doc.node_by_id(results[0]["new_model_version_id"])
    assert new is not None
    assert new["status"] == "active"
    assert "capability" not in new["attrs"]
    assert new["attrs"]["drift_fingerprint"] != "cn_baseline"

    # Prior observation still points at superseded version.
    obs_edge = [e for e in doc.edges if e["kind"] == "observed_on"][0]
    assert obs_edge["to"] == old_id
    supersedes = [e for e in doc.edges if e["kind"] == "supersedes"]
    assert len(supersedes) == 1
    assert supersedes[0]["to"] == old_id


def test_apply_fingerprint_shift_direct():
    doc = GraphDocument(
        schema=SCHEMA_ID,
        nodes=[
            {
                "id": "urn:mg:modelversion:x",
                "kind": "ModelVersion",
                "status": "active",
                "valid_start": "2026-01-01T00:00:00Z",
                "valid_end": None,
                "attrs": {"drift_fingerprint": "old"},
            }
        ],
        edges=[],
    )
    old, new, edge = apply_fingerprint_shift(
        doc, "urn:mg:modelversion:x", new_fingerprint="cn_new", at="2026-09-05T00:00:00Z"
    )
    assert old["status"] == "superseded"
    assert new["attrs"]["drift_fingerprint"] == "cn_new"
    assert edge["kind"] == "supersedes"


def test_canary_baseline_without_prior_fingerprint_does_not_supersede():
    old_id = "urn:mg:modelversion:fresh"
    doc = GraphDocument(
        schema=SCHEMA_ID,
        nodes=[
            {
                "id": old_id,
                "kind": "ModelVersion",
                "status": "active",
                "valid_start": "2026-01-01T00:00:00Z",
                "valid_end": None,
                "attrs": {"provider": "fixture"},
            }
        ],
        edges=[],
    )
    results = run_canaries(doc, model_version_ids=[old_id], canaries=load_canary_set(FIXTURE_CANARY))
    assert results[0]["changed"] is False
    assert results[0]["superseded"] is False
    assert doc.node_by_id(old_id)["status"] == "active"
    assert doc.node_by_id(old_id)["attrs"]["drift_fingerprint"]


def test_route_and_graph_do_not_import_probe_runner():
    for name in list(sys.modules):
        if name.startswith("compass.probe") or name in {
            "compass.route.decide",
            "compass.graph",
        }:
            del sys.modules[name]
    importlib.import_module("compass.route.decide")
    importlib.import_module("compass.graph")
    assert "compass.probe.runner" not in sys.modules


def test_no_real_api_key_literals_in_probe_sources():
    probe_dir = REPO_ROOT / "src" / "compass" / "probe"
    forbidden = ("sk-", "OPENAI_API_KEY=", "Bearer ")
    for path in probe_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} must not contain {token!r}"

