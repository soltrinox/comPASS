"""Paid Pillar 3 — managed fleet capability graph stub (test-ready).

Opt-in, anonymized, terms-safe. Default is local-only (free). Never receives
provider keys from clients — observations are already scored. Cards stay
priors; fleet data is not a public leaderboard.
"""

from __future__ import annotations

from compass.fleet.stub import (
    ENV_FLEET_OPT_IN,
    FleetCapabilityGraphStub,
    FleetIngestConfig,
    FleetIngestRefused,
    InMemorySharedGraphStore,
    SharedGraphStore,
    anonymize_snapshot,
    is_fleet_opt_in,
)

__all__ = [
    "ENV_FLEET_OPT_IN",
    "FleetCapabilityGraphStub",
    "FleetIngestConfig",
    "FleetIngestRefused",
    "InMemorySharedGraphStore",
    "SharedGraphStore",
    "anonymize_snapshot",
    "is_fleet_opt_in",
]
