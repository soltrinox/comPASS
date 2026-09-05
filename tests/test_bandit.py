"""Bandit posterior: score formula, persistence, update, allocate."""

from __future__ import annotations

from pathlib import Path

import pytest

from compass.score.bandit import BanditConfig, BanditPosterior, score


def test_score_formula():
    assert score(0.8, 0.1, 1.0) == pytest.approx(0.7)
    assert score(0.8, 0.1, 2.0) == pytest.approx(0.6)


def test_thompson_allocate_fail_open_empty():
    post = BanditPosterior(config=BanditConfig(allocator="thompson", seed=1))
    assert post.allocate("tc", []) is None


def test_thompson_allocate_returns_candidate():
    post = BanditPosterior(config=BanditConfig(allocator="thompson", seed=2))
    chosen = post.allocate("tc", ["m1", "m2"])
    assert chosen in {"m1", "m2"}


def test_ucb_allocate():
    post = BanditPosterior(config=BanditConfig(allocator="ucb", seed=3))
    arm = post.get_arm("tc", "poor")
    arm.alpha, arm.beta, arm.pulls = 1.0, 20.0, 20
    good = post.get_arm("tc", "good")
    good.alpha, good.beta, good.pulls = 20.0, 1.0, 20
    chosen = post.allocate("tc", ["poor", "good"])
    assert chosen in {"poor", "good"}


def test_expected_quality_default_on_empty_prior():
    post = BanditPosterior(config=BanditConfig(default_quality=0.42))
    arm = post.get_arm("tc", "m")
    arm.alpha = 0.0
    arm.beta = 0.0
    assert post.expected_quality(arm) == 0.42


def test_update_and_persist_roundtrip(tmp_path: Path):
    post = BanditPosterior(config=BanditConfig(allocator="thompson", seed=7, default_cost=0.2))
    post.update("code_generation", "m-good", reward=1.0, cost=0.1)
    post.update("code_generation", "m-good", reward=0.9, cost=0.12)
    post.update("code_generation", "m-poor", reward=0.0, cost=0.5)
    post.update("code_generation", "m-poor", reward=0.1, cost=0.55)
    path = tmp_path / "bandit-posterior.json"
    post.save(path)
    loaded = BanditPosterior.load(path)
    good = loaded.get_arm("code_generation", "m-good")
    poor = loaded.get_arm("code_generation", "m-poor")
    assert good.pulls == 2
    assert poor.pulls == 2
    assert good.alpha > poor.alpha
    assert loaded.expected_quality(good) > loaded.expected_quality(poor)
    # After enough evidence, UCB / thompson should prefer the good arm often
    chosen = loaded.allocate("code_generation", ["m-good", "m-poor"])
    assert chosen in {"m-good", "m-poor"}


def test_load_missing_fail_open(tmp_path: Path):
    post = BanditPosterior.load(tmp_path / "missing.json", fail_open=True)
    assert post.arms == {}


def test_load_corrupt_fail_open(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")
    post = BanditPosterior.load(path, fail_open=True)
    assert isinstance(post, BanditPosterior)
    assert post.arms == {}


def test_thompson_prefers_established_good_arm():
    """With strong evidence, Thompson should rarely pick the poor arm."""
    post = BanditPosterior(config=BanditConfig(allocator="thompson", seed=99))
    good = post.get_arm("tc", "good")
    good.alpha, good.beta, good.pulls = 40.0, 2.0, 40
    poor = post.get_arm("tc", "poor")
    poor.alpha, poor.beta, poor.pulls = 2.0, 40.0, 40
    picks = [post.allocate("tc", ["good", "poor"]) for _ in range(50)]
    assert picks.count("good") >= 40
