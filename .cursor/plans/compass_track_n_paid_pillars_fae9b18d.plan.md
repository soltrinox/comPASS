---
name: comPASS Track N — Paid pillars (test-ready)
overview: Implement or spike test-ready surfaces for automated cross-machine bundle sync, managed fleet capability graph stub, and enterprise governance policy hooks — each with acceptance tests linked to PAID-PILLARS.md.
todos:
  - id: pillar1-sync-automation
    content: "Spike/implement automated cross-machine bundle sync surface (paid); manual export/import remains free; acceptance tests"
    status: pending
  - id: pillar3-fleet-graph-stub
    content: "Managed fleet capability graph service stub — opt-in ingest API + anonymization hooks; terms-safe; acceptance tests"
    status: pending
  - id: pillar4-governance-hooks
    content: "Enterprise governance policy hooks — budget envelopes + eligibility filters as enforced routing constraints; acceptance tests"
    status: pending
  - id: link-paid-pillars-doc
    content: "Link each surface to docs/gtm/PAID-PILLARS.md with honest scope and non-claims (esp. Pillar 2 equivalence)"
    status: pending
  - id: free-vs-paid-tests
    content: "Tests proving manual bundle path stays free and sync automation is feature-gated as paid"
    status: pending
  - id: fleet-opt-in-default-off
    content: "Fleet stub defaults opt-out/local-only; no silent upload; document consent flag"
    status: pending
  - id: audit-trail-route-decision
    content: "Governance audit trail consumes persisted RouteDecision fields; fail-open when policy engine missing"
    status: pending
  - id: proof-n
    content: "Emit test-results/n-paid-pillars/ evidence for all three surfaces"
    status: pending
isProject: true
---

# comPASS Track N — Paid pillars (test-ready)

## Purpose

Turn GTM narrative in `docs/gtm/PAID-PILLARS.md` into **test-ready engineering surfaces** (implement or spike):

1. **Automated cross-machine bundle sync** (Pillar 1) — manual export/import stays free.
2. **Managed fleet capability graph service stub** (Pillar 3) — opt-in, anonymized, terms-safe.
3. **Enterprise governance policy hooks** (Pillar 4) — envelopes + eligibility as **enforcement**.

Pillar 2 (multi-model insertion) remains **measurement-gated** — do not claim bands until measured; this track may only ensure routing declines hops when band missing.

**Ground truth:** `docs/gtm/PAID-PILLARS.md`, `docs/gtm/FREE-TIER.md`, `docs/gtm/ENTERPRISE.md`, `src/compass/bundle.py`, Route envelopes.

**Depends on:** Track L (versioned package) + Track F (live probe story for fleet). Track G soft (audit/reward richness).

## Locked defaults

- Fail-open when sync/fleet/governance services are absent → local free path.
- Probe never on prompt path; fleet stub does not receive provider keys from clients (observations already scored).
- No keys in WASM.
- No identical-text claims; Pillar 2 public copy stays blocked until bands exist.
- Fleet redistribution obeys Track F ToS denylist.

## Deliverable paths

```
comPASS/
  src/compass/
    sync/                               # NEW — automation (paid gate)
    fleet/                              # NEW — service stub
    serve/governance.py                 # NEW or extend envelope.py
  docs/gtm/PAID-PILLARS.md              # link engineering sections
  docs/gtm/PAID-SURFACES.md             # NEW map code ↔ pillars
  tests/test_paid_sync.py               # NEW
  tests/test_fleet_stub.py              # NEW
  tests/test_governance_hooks.py        # NEW
  test-results/n-paid-pillars/
```

## Acceptance / test criteria

1. **Sync:** automated path feature-flagged; manual bundle export/import tests still pass without flag.
2. **Fleet stub:** local-only default; opt-in flag required; anonymization hook invoked before any outbound; denylist consulted.
3. **Governance:** policy denying an endpoint causes Route to select eligible alternative or fail-open default **without** raising to the user as a hard block unless policy says enforce-block (document which); audit record written.
4. `PAID-SURFACES.md` links each pillar section to code + tests.
5. Evidence folder with three graded proofs.

## Dependencies

| Depends on | L + F (required per master order); G soft |
| Unblocks | Sales/demo of paid surfaces without claiming production fleet |

## Explicit non-goals

- Full multi-region sync SaaS.
- Real multi-tenant fleet production hardening.
- SSO/RBAC complete IdP integration (hooks/stubs only).
- Publishing Pillar 2 equivalence marketing numbers.
