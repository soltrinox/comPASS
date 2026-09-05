"""Provider ToS / automated-benchmarking denylist (hard gates).

Comparative Observation payloads marked for fleet redistribution are blocked
when the provider forbids automated benchmarking or public comparative use.
This is a hard gate, not a warning — see docs/probe/TERMS-CHECKLIST.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

# Providers whose terms restrict automated benchmarking and/or fleet
# redistribution of comparative rankings. Keys are normalized provider ids.
PROVIDER_TOS: dict[str, dict[str, Any]] = {
    "openai": {
        "automated_benchmarking": "deny",
        "fleet_comparative_redistribute": "deny",
        "notes": "Do not redistribute comparative probe ranks derived from OpenAI endpoints.",
    },
    "anthropic": {
        "automated_benchmarking": "deny",
        "fleet_comparative_redistribute": "deny",
        "notes": "Do not redistribute comparative probe ranks derived from Anthropic endpoints.",
    },
    "google": {
        "automated_benchmarking": "review",
        "fleet_comparative_redistribute": "deny",
        "notes": "Comparative publication requires review; default deny for fleet redistribute.",
    },
    "huggingface": {
        "automated_benchmarking": "allow_local",
        "fleet_comparative_redistribute": "allow_anonymized",
        "notes": "Local probes OK; fleet redistribute only anonymized outcome-equivalence stats.",
    },
    "openrouter": {
        "automated_benchmarking": "allow_local",
        "fleet_comparative_redistribute": "allow_anonymized",
        "notes": "Respect upstream model provider terms when probing via OpenRouter.",
    },
    "cursor": {
        "automated_benchmarking": "allow_local",
        "fleet_comparative_redistribute": "deny",
        "notes": "Cursor catalog/canary local OK; no fleet comparative redistribution.",
    },
}

# Hard denylist: never mark these for fleet redistribute of comparative outputs.
FLEET_COMPARATIVE_DENYLIST = frozenset(
    p for p, meta in PROVIDER_TOS.items() if meta.get("fleet_comparative_redistribute") == "deny"
)

AUTOMATED_BENCHMARK_DENYLIST = frozenset(
    p for p, meta in PROVIDER_TOS.items() if meta.get("automated_benchmarking") == "deny"
)


class TosViolation(RuntimeError):
    """Raised when an Observation would violate provider ToS redistribution rules."""


@dataclass(frozen=True)
class TosDecision:
    provider: str
    allowed: bool
    reason: str
    fleet_redistribute: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "allowed": self.allowed,
            "reason": self.reason,
            "fleet_redistribute": self.fleet_redistribute,
        }


def normalize_provider(provider: str | None) -> str:
    return (provider or "").strip().lower()


def evaluate_tos(
    provider: str | None,
    *,
    for_fleet_redistribute: bool = False,
    comparative: bool = True,
) -> TosDecision:
    """Evaluate whether an action is allowed under the hard ToS policy."""
    p = normalize_provider(provider)
    meta = PROVIDER_TOS.get(p)
    if meta is None:
        # Unknown provider: allow local observations; deny fleet comparative by default.
        if for_fleet_redistribute and comparative:
            return TosDecision(
                provider=p or "unknown",
                allowed=False,
                reason="unknown provider — deny fleet comparative redistribution by default",
                fleet_redistribute=False,
            )
        return TosDecision(
            provider=p or "unknown",
            allowed=True,
            reason="unknown provider — local-only observation permitted",
            fleet_redistribute=False,
        )

    if for_fleet_redistribute and comparative:
        policy = meta.get("fleet_comparative_redistribute")
        if policy == "deny" or p in FLEET_COMPARATIVE_DENYLIST:
            return TosDecision(
                provider=p,
                allowed=False,
                reason=str(meta.get("notes") or "fleet comparative redistribute denied"),
                fleet_redistribute=False,
            )
        if policy == "allow_anonymized":
            return TosDecision(
                provider=p,
                allowed=True,
                reason="anonymized outcome-equivalence stats only",
                fleet_redistribute=True,
            )
        return TosDecision(
            provider=p,
            allowed=False,
            reason=f"unsupported fleet policy {policy!r}",
            fleet_redistribute=False,
        )

    if comparative and p in AUTOMATED_BENCHMARK_DENYLIST:
        return TosDecision(
            provider=p,
            allowed=False,
            reason=str(meta.get("notes") or "automated benchmarking denied"),
            fleet_redistribute=False,
        )

    return TosDecision(
        provider=p,
        allowed=True,
        reason=str(meta.get("notes") or "allowed"),
        fleet_redistribute=False,
    )


def assert_fleet_redistribution_allowed(observation: Mapping[str, Any]) -> None:
    """Hard gate: raise if Observation is marked for forbidden fleet redistribute."""
    attrs = observation.get("attrs") if isinstance(observation.get("attrs"), Mapping) else observation
    if not isinstance(attrs, Mapping):
        return
    if not attrs.get("fleet_redistribute"):
        return
    provider = attrs.get("provider") or attrs.get("source_provider")
    comparative = bool(attrs.get("comparative", True))
    decision = evaluate_tos(str(provider) if provider else None, for_fleet_redistribute=True, comparative=comparative)
    if not decision.allowed:
        raise TosViolation(
            f"refusing fleet redistribute for provider={decision.provider!r}: {decision.reason}"
        )


def gate_observation_payload(attrs: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of attrs with fleet_redistribute forced off when denylisted.

    If the caller explicitly requested fleet_redistribute=True on a denylisted
    provider, raise ``TosViolation`` instead of silently dropping (hard gate).
    """
    out = dict(attrs)
    provider = out.get("provider") or out.get("source_provider")
    want_fleet = bool(out.get("fleet_redistribute"))
    comparative = bool(out.get("comparative", True))
    decision = evaluate_tos(
        str(provider) if provider else None,
        for_fleet_redistribute=want_fleet,
        comparative=comparative,
    )
    if want_fleet and not decision.allowed:
        raise TosViolation(
            f"refusing to write forbidden comparative Observation for "
            f"provider={decision.provider!r}: {decision.reason}"
        )
    out["tos"] = decision.to_dict()
    if not decision.fleet_redistribute:
        out["fleet_redistribute"] = False
    # Never claim public leaderboard rank from probe data.
    out.pop("leaderboard_rank", None)
    out["public_leaderboard"] = False
    return out


__all__ = [
    "AUTOMATED_BENCHMARK_DENYLIST",
    "FLEET_COMPARATIVE_DENYLIST",
    "PROVIDER_TOS",
    "TosDecision",
    "TosViolation",
    "assert_fleet_redistribution_allowed",
    "evaluate_tos",
    "gate_observation_payload",
    "normalize_provider",
]
