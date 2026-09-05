# Paid surfaces ↔ engineering map (Track N)

Test-ready spikes only — **not** full SaaS productization. Linked from
[PAID-PILLARS.md](PAID-PILLARS.md). Free-tier paths stay unchanged
([FREE-TIER.md](FREE-TIER.md)).

**Non-claim:** never identical or near-identical cross-model output text.
Pillar 2 public marketing remains blocked until outcome-equivalence bands
are measured.

| Pillar | Code | Tests | Evidence |
|---|---|---|---|
| 1 — Automated cross-machine sync | `src/compass/sync/` (`local_bundle.py`, `automation.py`); free manual via `compass.bundle` + `export_local_bundle` | `tests/test_paid_sync.py` | `test-results/n-paid-pillars/` |
| 3 — Managed fleet capability graph | `src/compass/fleet/stub.py` | `tests/test_fleet_stub.py` | same |
| 4 — Enterprise governance | `src/compass/serve/governance.py` (enforced in `route/decide.py` + proxy) | `tests/test_governance_hooks.py` | same |
| 2 — Multi-model insertion | *not implemented this track* — router may decline hops when band missing; no marketing numbers | — | — |
| 5 — Team shared memory | *not this track* (depends on Pillar 1 productization) | — | — |

## Feature gates / consent

| Surface | Default | Enable |
|---|---|---|
| Automated sync | OFF (manual export/import free) | `COMPASS_PAID_SYNC=1` or `SyncAutomationConfig(enabled=True)` |
| Fleet ingest | OFF (local-only graph free) | `COMPASS_FLEET_OPT_IN=1` or `FleetIngestConfig(opt_in=True)` |
| Governance | OFF (no policy → unconstrained fail-open) | pass `policy={...}` into `decide` / `ProxyConfig` |

## Fail-open summary

- Sync automation absent/disabled → use manual bundle path; no Route impact.
- Fleet stub without opt-in → refuse ingest; local graph unchanged.
- Governance engine missing/corrupt → Route ignores policy tags `governance:missing_engine`.
- Governance denies all candidates → fail-open to configured default unless `enforce_block` (still returns a decision; never raises on the prompt path).

## Still productization (explicit non-goals of Track N)

- Multi-region sync SaaS, conflict UX, E2E encryption at rest for sync.
- Real multi-tenant fleet hardening, billing, consent UI, legal redistribution pipeline.
- SSO/RBAC IdP integration, complete audit warehouse, DLP product.
- Pillar 2 measured equivalence bands / managed insertion service.
- Pillar 5 shared project memory.
