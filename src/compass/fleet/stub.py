"""Managed fleet capability graph — in-process multi-tenant ingest stub.

Constraints (docs/gtm/PAID-PILLARS.md Pillar 3 + Track F ToS):
- Default opt-out / local-only (``COMPASS_FLEET_OPT_IN`` unset/0).
- Anonymization hook runs before any shared-store write.
- Fleet comparative redistribute consults ``compass.probe.tos_policy``.
- No provider keys accepted or stored.
- No public leaderboard ranks.
"""

from __future__ import annotations

import hashlib
import os
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, runtime_checkable

from compass.probe.tos_policy import TosViolation, evaluate_tos, gate_observation_payload

ENV_FLEET_OPT_IN = "COMPASS_FLEET_OPT_IN"


class FleetIngestRefused(RuntimeError):
    """Raised when fleet ingest is attempted without consent / against ToS."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_fleet_opt_in(*, config: "FleetIngestConfig | None" = None) -> bool:
    if config is not None and config.opt_in is not None:
        return bool(config.opt_in)
    raw = os.environ.get(ENV_FLEET_OPT_IN, "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def anonymize_snapshot(snapshot: Mapping[str, Any], *, tenant_id: str) -> dict[str, Any]:
    """Strip PII / keys / absolute paths; hash tenant id for shared graph.

    Invoked before any outbound / shared-store write.
    """
    out = deepcopy(dict(snapshot))
    # Never carry secrets or machine paths.
    for key in list(out.keys()):
        lk = key.lower()
        if any(s in lk for s in ("key", "token", "secret", "password", "authorization")):
            out.pop(key, None)
        if lk.endswith("_path") or lk in {"home", "cwd", "abspath"}:
            out.pop(key, None)
    tenant_hash = hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()[:16]
    out["tenant_pseudonym"] = f"t_{tenant_hash}"
    out.pop("tenant_id", None)
    out.pop("user_id", None)
    out.pop("email", None)
    out.pop("hostname", None)
    # Observations / catalog nodes
    nodes = out.get("nodes")
    if isinstance(nodes, list):
        cleaned: list[dict[str, Any]] = []
        for node in nodes:
            if not isinstance(node, Mapping):
                continue
            n = deepcopy(dict(node))
            attrs = n.get("attrs") if isinstance(n.get("attrs"), Mapping) else {}
            attrs = dict(attrs)
            for bad in ("api_key", "token", "prompt", "raw_response", "user_email"):
                attrs.pop(bad, None)
            attrs["tenant_pseudonym"] = out["tenant_pseudonym"]
            attrs.pop("tenant_id", None)
            # Force ToS gate shape; comparative fleet flags must pass denylist.
            try:
                attrs = gate_observation_payload(attrs)
            except TosViolation:
                # Drop forbidden comparative nodes rather than poisoning the store.
                continue
            n["attrs"] = attrs
            cleaned.append(n)
        out["nodes"] = cleaned
    out["anonymized"] = True
    out["anonymized_at"] = _now_iso()
    out["public_leaderboard"] = False
    return out


@runtime_checkable
class SharedGraphStore(Protocol):
    """Shared graph store interface (in-process OK for this spike)."""

    def upsert_nodes(self, nodes: list[dict[str, Any]], *, source: str) -> int: ...

    def snapshot(self) -> dict[str, Any]: ...


@dataclass
class InMemorySharedGraphStore:
    """Process-local multi-tenant graph merge (not production multi-region)."""

    nodes_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    ingest_log: list[dict[str, Any]] = field(default_factory=list)

    def upsert_nodes(self, nodes: list[dict[str, Any]], *, source: str) -> int:
        n = 0
        for node in nodes:
            nid = str(node.get("id") or "")
            if not nid:
                continue
            self.nodes_by_id[nid] = deepcopy(node)
            n += 1
        self.ingest_log.append(
            {"at": _now_iso(), "source": source, "count": n}
        )
        return n

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": "model-graph/v1",
            "nodes": list(self.nodes_by_id.values()),
            "edges": [],
            "fleet": True,
            "public_leaderboard": False,
        }


@dataclass
class FleetIngestConfig:
    """Consent + safety knobs. ``opt_in=None`` defers to ``COMPASS_FLEET_OPT_IN``."""

    opt_in: bool | None = None
    require_anonymization: bool = True
    # When False, refused ingest returns a result dict instead of raising.
    fail_open: bool = True


@dataclass
class FleetIngestResult:
    ok: bool
    opted_in: bool
    ingested: int = 0
    reason: str | None = None
    tenant_pseudonym: str | None = None
    tos_blocked: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "opted_in": self.opted_in,
            "ingested": self.ingested,
            "reason": self.reason,
            "tenant_pseudonym": self.tenant_pseudonym,
            "tos_blocked": self.tos_blocked,
        }


class FleetCapabilityGraphStub:
    """Service stub: ingest multi-tenant Observation/catalog snapshots."""

    def __init__(
        self,
        store: SharedGraphStore | None = None,
        config: FleetIngestConfig | None = None,
    ) -> None:
        self.store: SharedGraphStore = store or InMemorySharedGraphStore()
        self.config = config or FleetIngestConfig()

    def ingest(
        self,
        tenant_id: str,
        snapshot: Mapping[str, Any],
        *,
        source: str = "observation",
    ) -> FleetIngestResult:
        """Ingest a tenant snapshot into the shared graph (opt-in required)."""
        opted = is_fleet_opt_in(config=self.config)
        if not opted:
            reason = (
                f"fleet ingest refused — opt-in required "
                f"(set {ENV_FLEET_OPT_IN}=1 or FleetIngestConfig(opt_in=True)); "
                "local-only graph remains free"
            )
            if self.config.fail_open:
                return FleetIngestResult(ok=False, opted_in=False, reason=reason)
            raise FleetIngestRefused(reason)

        # Count ToS-blocked comparative nodes before anonymize drops them.
        tos_blocked = 0
        raw_nodes = snapshot.get("nodes") if isinstance(snapshot.get("nodes"), list) else []
        for node in raw_nodes:
            if not isinstance(node, Mapping):
                continue
            attrs = node.get("attrs") if isinstance(node.get("attrs"), Mapping) else {}
            if attrs.get("fleet_redistribute"):
                provider = attrs.get("provider") or attrs.get("source_provider")
                decision = evaluate_tos(
                    str(provider) if provider else None,
                    for_fleet_redistribute=True,
                    comparative=bool(attrs.get("comparative", True)),
                )
                if not decision.allowed:
                    tos_blocked += 1

        if self.config.require_anonymization:
            clean = anonymize_snapshot(snapshot, tenant_id=tenant_id)
        else:
            clean = deepcopy(dict(snapshot))

        nodes = clean.get("nodes") if isinstance(clean.get("nodes"), list) else []
        # Catalog-shaped snapshots without nodes: wrap quality priors as nodes.
        if not nodes and "models" in clean:
            nodes = []
            for m in clean.get("models") or []:
                if not isinstance(m, Mapping):
                    continue
                mid = str(m.get("id") or m.get("model_version_id") or "")
                if not mid:
                    continue
                nodes.append(
                    {
                        "id": f"urn:mg:fleet:{clean.get('tenant_pseudonym', 'x')}:{mid}",
                        "kind": "Observation",
                        "status": "active",
                        "attrs": gate_observation_payload(
                            {
                                "model_version_id": mid,
                                "provider": m.get("provider"),
                                "quality": m.get("quality") or {"mean": 0.5, "n": 0, "ci95": 1.0},
                                "cost": m.get("cost") or {"mean": 0.0, "n": 0, "ci95": 0.0},
                                "fleet_redistribute": bool(m.get("fleet_redistribute", False)),
                                "comparative": bool(m.get("comparative", False)),
                                "tenant_pseudonym": clean.get("tenant_pseudonym"),
                            }
                        ),
                    }
                )

        count = self.store.upsert_nodes(list(nodes), source=f"{source}:{clean.get('tenant_pseudonym')}")
        return FleetIngestResult(
            ok=True,
            opted_in=True,
            ingested=count,
            tenant_pseudonym=str(clean.get("tenant_pseudonym")),
            tos_blocked=tos_blocked,
        )


__all__ = [
    "ENV_FLEET_OPT_IN",
    "FleetCapabilityGraphStub",
    "FleetIngestConfig",
    "FleetIngestRefused",
    "FleetIngestResult",
    "InMemorySharedGraphStore",
    "SharedGraphStore",
    "anonymize_snapshot",
    "is_fleet_opt_in",
]
