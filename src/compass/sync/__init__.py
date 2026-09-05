"""Paid Pillar 1 — automated cross-machine bundle sync (test-ready spike).

Manual export/import of the portable bundle format stays **free**
(see docs/gtm/FREE-TIER.md Appendix A.5). Only *automated* push/pull
round-trips are feature-gated as paid.

When chat-compressor CC-8 is installed, ``compass.bundle`` delegates to it;
otherwise a comPASS-local bundle layout (manifest + graph JSON) is used.
"""

from __future__ import annotations

from compass.sync.automation import (
    ENV_PAID_SYNC,
    AutomatedSync,
    PaidFeatureDisabled,
    SyncAutomationConfig,
    is_paid_sync_enabled,
)
from compass.sync.local_bundle import (
    export_local_bundle,
    import_local_bundle,
    verify_bundle,
)

__all__ = [
    "ENV_PAID_SYNC",
    "AutomatedSync",
    "PaidFeatureDisabled",
    "SyncAutomationConfig",
    "export_local_bundle",
    "import_local_bundle",
    "is_paid_sync_enabled",
    "verify_bundle",
]
