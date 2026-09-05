"""Automated cross-machine sync — **paid** feature gate (Pillar 1).

Manual ``export_local_bundle`` / ``import_local_bundle`` remain free.
Automated round-trip helpers require ``COMPASS_PAID_SYNC=1`` (or
``SyncAutomationConfig(enabled=True)``).

Fail-open: when the paid gate is off, callers get ``PaidFeatureDisabled``
(or ``fail_open=True`` returns a structured refusal) so free paths continue
via manual export/import.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from compass.sync.local_bundle import export_local_bundle, import_local_bundle, verify_bundle

ENV_PAID_SYNC = "COMPASS_PAID_SYNC"


class PaidFeatureDisabled(RuntimeError):
    """Raised when automated sync is invoked without the paid feature flag."""


def is_paid_sync_enabled(*, config: "SyncAutomationConfig | None" = None) -> bool:
    if config is not None and config.enabled is not None:
        return bool(config.enabled)
    raw = os.environ.get(ENV_PAID_SYNC, "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


@dataclass
class SyncAutomationConfig:
    """Paid sync knobs. ``enabled=None`` defers to ``COMPASS_PAID_SYNC``."""

    enabled: bool | None = None
    agent_id: str = "local"
    # When True, missing paid flag returns a refusal dict instead of raising.
    fail_open: bool = True


@dataclass
class SyncResult:
    ok: bool
    paid: bool
    action: str
    source: str | None = None
    dest: str | None = None
    bundle: str | None = None
    reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "paid": self.paid,
            "action": self.action,
            "source": self.source,
            "dest": self.dest,
            "bundle": self.bundle,
            "reason": self.reason,
            "details": dict(self.details),
        }


class AutomatedSync:
    """API/scripts surface for paid automated export → transfer → import."""

    def __init__(self, config: SyncAutomationConfig | None = None) -> None:
        self.config = config or SyncAutomationConfig()

    def _gate(self, action: str) -> SyncResult | None:
        if is_paid_sync_enabled(config=self.config):
            return None
        reason = (
            f"automated sync requires paid gate ({ENV_PAID_SYNC}=1); "
            "manual export/import remains free"
        )
        if self.config.fail_open:
            return SyncResult(
                ok=False,
                paid=False,
                action=action,
                reason=reason,
                details={"free_path": "compass.sync.local_bundle / compass.bundle"},
            )
        raise PaidFeatureDisabled(reason)

    def automate_export(self, graph_root: str | Path, bundle_dest: str | Path) -> SyncResult:
        blocked = self._gate("automate_export")
        if blocked is not None:
            return blocked
        out = export_local_bundle(
            graph_root, bundle_dest, agent_id=self.config.agent_id
        )
        man = verify_bundle(out)
        return SyncResult(
            ok=True,
            paid=True,
            action="automate_export",
            source=str(graph_root),
            bundle=str(out),
            details={"manifest_schema": man.get("schema"), "checksums": man.get("checksums")},
        )

    def automate_import(self, bundle_root: str | Path, dest_graph_root: str | Path) -> SyncResult:
        blocked = self._gate("automate_import")
        if blocked is not None:
            return blocked
        dest = import_local_bundle(bundle_root, dest_graph_root)
        return SyncResult(
            ok=True,
            paid=True,
            action="automate_import",
            dest=str(dest),
            bundle=str(bundle_root),
        )

    def round_trip(
        self,
        source_graph_root: str | Path,
        dest_graph_root: str | Path,
        *,
        staging_dir: str | Path | None = None,
    ) -> SyncResult:
        """Export from source, stage, import into dest — paid automation path."""
        blocked = self._gate("round_trip")
        if blocked is not None:
            return blocked
        stage = Path(staging_dir) if staging_dir else Path(dest_graph_root).parent / "_sync_stage"
        if stage.exists():
            shutil.rmtree(stage)
        exp = self.automate_export(source_graph_root, stage / "bundle")
        if not exp.ok:
            return exp
        imp = self.automate_import(stage / "bundle", dest_graph_root)
        if not imp.ok:
            return imp
        return SyncResult(
            ok=True,
            paid=True,
            action="round_trip",
            source=str(source_graph_root),
            dest=str(dest_graph_root),
            bundle=str(stage / "bundle"),
            details={"export": exp.to_dict(), "import": imp.to_dict()},
        )


__all__ = [
    "ENV_PAID_SYNC",
    "AutomatedSync",
    "PaidFeatureDisabled",
    "SyncAutomationConfig",
    "SyncResult",
    "is_paid_sync_enabled",
]
