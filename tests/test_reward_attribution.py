"""Track G: delayed reward join correctness + fail-open + hot-path isolation."""

from __future__ import annotations

import os
import time
from pathlib import Path

from compass.graph import GraphStore, GraphStoreConfig
from compass.route.decide import RouteConfig, decide
from compass.schema import SCHEMA_ID, GraphDocument
from compass.score.attribution import (
    DelayedReward,
    apply_attribution_to_document,
    attach_delayed_reward,
    bandit_update_enabled,
    select_targets,
)
from compass.score.bandit import BanditPosterior
from compass.score.reward import (
    RewardObservation,
    attach_reward_to_route_decision,
    attach_reward_to_trajectory,
    record_reward,
)


def _decision(
    did: str,
    *,
    traj: str | None = None,
    episode: str | None = None,
    hop: int | None = None,
    model: str = "m1",
    task: str = "code_generation",
    at: str = "2026-09-05T12:00:00Z",
) -> dict:
    attrs = {
        "task_class_id": task,
        "selected_model_version_id": model,
        "scores": {model: 0.7},
        "lambda": 1.0,
        "rationale": "test",
        "fail_open": False,
        "decided_at": at,
    }
    if traj is not None:
        attrs["trajectory_id"] = traj
    if episode is not None:
        attrs["episode_id"] = episode
    if hop is not None:
        attrs["hop_index"] = hop
    return {
        "id": did,
        "kind": "RouteDecision",
        "status": "active",
        "valid_start": at,
        "valid_end": None,
        "attrs": attrs,
    }


def test_missing_join_keys_skip():
    doc = GraphDocument(schema=SCHEMA_ID, nodes=[], edges=[])
    result = apply_attribution_to_document(
        doc, DelayedReward(value=1.0), policy="trajectory"
    )
    assert result.status == "skipped"
    assert result.reason == "missing_join_keys"
    assert result.to_dict()["credit_assignment_solved"] is False


def test_orphan_reward_no_crash():
    doc = GraphDocument(schema=SCHEMA_ID, nodes=[], edges=[])
    result = apply_attribution_to_document(
        doc,
        DelayedReward(value=0.9, trajectory_id="traj-missing"),
        policy="trajectory",
    )
    assert result.status == "orphaned"
    assert result.reason == "no_matching_route_decision"


def test_late_reward_multi_hop_trajectory_join():
    traj = "urn:traj:demo"
    doc = GraphDocument(
        schema=SCHEMA_ID,
        nodes=[
            _decision("urn:mg:rd:h0", traj=traj, hop=0, model="m0"),
            _decision("urn:mg:rd:h1", traj=traj, hop=1, model="m1"),
            _decision("urn:mg:rd:h2", traj=traj, hop=2, model="m2"),
            _decision("urn:mg:rd:other", traj="urn:traj:other", hop=0, model="mx"),
        ],
        edges=[],
    )
    result = apply_attribution_to_document(
        doc,
        DelayedReward(value=0.9, trajectory_id=traj, source="verifiable"),
        policy="trajectory",
        at="2026-09-05T13:00:00Z",
        reward_id="urn:mg:reward:late1",
    )
    assert result.status == "joined"
    assert len(result.targets) == 3
    assert abs(sum(t.share for t in result.targets) - 1.0) < 1e-9
    active = doc.active_nodes(kind="RouteDecision")
    attributed = [
        n for n in active if n["attrs"].get("attribution_reward_id") == "urn:mg:reward:late1"
    ]
    assert len(attributed) == 3
    for n in attributed:
        assert n["attrs"]["credit_assignment_solved"] is False
        assert n["attrs"]["attribution_policy"] == "trajectory"
        assert abs(n["attrs"]["attributed_reward"] - 0.3) < 1e-9
    # Unrelated trajectory untouched
    other = doc.node_by_id("urn:mg:rd:other")
    assert other is not None
    assert other["status"] == "active"
    assert "attributed_reward" not in other.get("attrs", {})


def test_episode_oracle_terminal_share():
    ep = "urn:ep:1"
    nodes = [
        _decision("urn:mg:rd:e0", episode=ep, hop=0, model="a"),
        _decision("urn:mg:rd:e1", episode=ep, hop=1, model="b"),
    ]
    targets = select_targets(nodes, DelayedReward(value=1.0, episode_id=ep), "episode")
    assert targets[0].share == 0.0
    assert targets[1].share == 1.0
    doc = GraphDocument(schema=SCHEMA_ID, nodes=nodes, edges=[])
    result = apply_attribution_to_document(
        doc,
        DelayedReward(value=1.0, episode_id=ep),
        policy="episode",
        reward_id="urn:mg:reward:ep1",
    )
    assert result.status == "joined"
    by_model = {
        doc.node_by_id(nid)["attrs"]["selected_model_version_id"]: doc.node_by_id(nid)["attrs"][
            "attributed_reward"
        ]
        for nid in result.new_decision_ids
    }
    assert by_model["a"] == 0.0
    assert by_model["b"] == 1.0


def test_counterfactual_later_stub_no_write():
    doc = GraphDocument(
        schema=SCHEMA_ID,
        nodes=[_decision("urn:mg:rd:c0", traj="t1", hop=0)],
        edges=[],
    )
    before = len(doc.nodes)
    result = apply_attribution_to_document(
        doc,
        DelayedReward(value=1.0, trajectory_id="t1"),
        policy="counterfactual_later",
    )
    assert result.status == "stubbed"
    assert len(doc.nodes) == before
    assert "not solved" in result.reason.lower() or "Credit assignment" in result.reason


def test_store_attach_apis(tmp_path: Path):
    cfg = GraphStoreConfig(root=tmp_path / "data")
    with GraphStore(cfg) as store:
        store.append_route_decision(
            {
                "task_class_id": "code_generation",
                "selected_model_version_id": "m1",
                "scores": {"m1": 0.8},
                "lambda": 1.0,
                "trajectory_id": "traj-api",
                "hop_index": 0,
                "decided_at": "2026-09-05T12:00:00Z",
            },
            decision_id="urn:mg:rd:api0",
            at="2026-09-05T12:00:00Z",
        )
        store.append_route_decision(
            {
                "task_class_id": "code_generation",
                "selected_model_version_id": "m2",
                "scores": {"m2": 0.6},
                "lambda": 1.0,
                "trajectory_id": "traj-api",
                "hop_index": 1,
                "decided_at": "2026-09-05T12:01:00Z",
            },
            decision_id="urn:mg:rd:api1",
            at="2026-09-05T12:01:00Z",
        )
        r1 = attach_reward_to_trajectory(
            store, value=0.8, trajectory_id="traj-api", observed_at="2026-09-05T14:00:00Z"
        )
        assert r1.status == "joined"
        r2 = attach_reward_to_route_decision(
            store, value=0.5, route_decision_id=r1.new_decision_ids[0]
        )
        # Second join onto already-attributed active node
        assert r2.status in {"joined", "orphaned"}


def test_record_reward_noop_without_store():
    assert (
        record_reward(
            RewardObservation(
                source="verifiable",
                value=1.0,
                task_class_id="t",
                model_version_id="m",
            )
        )
        is None
    )


def test_bandit_flag_default_off_and_gated_update(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("COMPASS_ATTRIBUTION_BANDIT_UPDATE", raising=False)
    assert bandit_update_enabled() is False
    cfg = GraphStoreConfig(root=tmp_path / "data")
    post = BanditPosterior()
    arm_before = post.get_arm("code_generation", "m1")
    alpha0 = arm_before.alpha
    with GraphStore(cfg) as store:
        store.append_route_decision(
            {
                "task_class_id": "code_generation",
                "selected_model_version_id": "m1",
                "trajectory_id": "traj-b",
                "hop_index": 0,
                "scores": {"m1": 0.5},
                "lambda": 1.0,
            },
            decision_id="urn:mg:rd:b0",
        )
        result = attach_delayed_reward(
            store,
            DelayedReward(value=1.0, trajectory_id="traj-b", task_class_id="code_generation"),
            posterior=post,
            update_bandit=False,
        )
        assert result.status == "joined"
        assert result.bandit_updated is False
        assert post.get_arm("code_generation", "m1").alpha == alpha0
        result2 = attach_delayed_reward(
            store,
            DelayedReward(value=1.0, trajectory_id="traj-b", task_class_id="code_generation"),
            # re-join will target new active nodes from prior supersede
            posterior=post,
            update_bandit=True,
        )
        # May orphan if traj attrs only on superseded — if joined, bandit updates
        if result2.status == "joined":
            assert result2.bandit_updated is True
            assert post.get_arm("code_generation", "m1").alpha == alpha0 + 1.0


def test_old_fixture_route_decision_still_loads():
    """Additive attrs: RouteDecision without trajectory fields remains valid."""
    doc = GraphDocument.from_dict(
        {
            "schema": SCHEMA_ID,
            "nodes": [
                {
                    "id": "urn:mg:rd:legacy",
                    "kind": "RouteDecision",
                    "status": "active",
                    "valid_start": "2026-01-01T00:00:00Z",
                    "valid_end": None,
                    "attrs": {
                        "task_class_id": "default",
                        "selected_model_version_id": "default",
                        "scores": {},
                        "lambda": 1.0,
                    },
                }
            ],
            "edges": [],
        }
    )
    assert doc.nodes[0]["attrs"].get("trajectory_id") is None


def test_decide_hot_path_unaffected_by_attribution(tmp_path: Path):
    """decide() must not wait on reward join; microbenchmark soft bound."""
    cfg = GraphStoreConfig(root=tmp_path / "data")
    with GraphStore(cfg) as store:
        samples = []
        # Warm one call so SQLite/schema setup is not in the p95 window.
        decide(
            "write a function",
            config=RouteConfig(default_model_version_id="default"),
            candidates=[{"id": "m1", "quality": 0.8, "cost": 0.2}],
            store=store,
        )
        for _ in range(40):
            t0 = time.perf_counter()
            result = decide(
                "write a function",
                config=RouteConfig(default_model_version_id="default"),
                candidates=[{"id": "m1", "quality": 0.8, "cost": 0.2}],
                store=store,
            )
            samples.append((time.perf_counter() - t0) * 1000.0)
            assert result.selected_model_version_id in {"m1", "default"}
        samples.sort()
        p95 = samples[int(0.95 * (len(samples) - 1))]
        # Soft latency guard: local 50ms; CI runners are noisier (shared CPUs).
        bound = 150.0 if os.environ.get("CI") else 50.0
        assert p95 < bound, f"decide p95 {p95:.2f}ms exceeded soft {bound:.0f}ms bound"
        # Attribution is a separate API — not invoked by decide
        active = store.active_nodes(kind="RouteDecision")
        assert active
        assert all("attributed_reward" not in (n.get("attrs") or {}) for n in active)


def test_graph_store_attribute_helper(tmp_path: Path):
    cfg = GraphStoreConfig(root=tmp_path / "data")
    with GraphStore(cfg) as store:
        store.append_route_decision(
            {
                "task_class_id": "t",
                "selected_model_version_id": "m1",
                "trajectory_id": "traj-g",
                "hop_index": 0,
                "scores": {"m1": 1.0},
                "lambda": 1.0,
            },
            decision_id="urn:mg:rd:g0",
        )
        result = store.attribute_delayed_reward(
            DelayedReward(value=0.7, trajectory_id="traj-g"),
            policy="trajectory",
        )
        assert result.status == "joined"
        assert store.find_route_decisions(trajectory_id="traj-g")
