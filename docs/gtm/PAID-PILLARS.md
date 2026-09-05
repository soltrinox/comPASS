# Five paid pillars

Paid sells **marginal cost** and **network effects**. Free already includes correctness (see [FREE-TIER.md](FREE-TIER.md)).

**Recurring-revenue core:** lead with **Pillar 3 (managed capability graph / fleet probes)** — ongoing probe spend, ongoing drift, ongoing catalog churn. Pillars 1/5 are storage+sync. Pillar 4 is seat+support. Pillar 2 is a measured capability, not a vibe.

---

## Pillar 1 — Cross-machine context migration

**What:** The context graph, the quantized tensor index, the state lineage, and the per-recipient injection ledger travel with the user across machines, encrypted end to end. Start on a laptop, continue on a workstation, resume from a cloud agent, lineage intact.

**Why hard to self-host:** Storage, transfer, conflict resolution (prototype §15). Conflict when two machines advance the same `agent_id` → branch at graph level (union + supersession), **not** last-write-wins on tensors. First release may present divergence as a user choice.

**Depends on:** Track B **CC-8** (bundle) and **CC-10** (quantization; index is **not** quantized today — float32 safetensors).

**Honest scope:** Manual export/import of the same format remains free ([FREE-TIER.md](FREE-TIER.md) Appendix A.5 closed decision). Only automated sync is paid.

---

## Pillar 2 — Multi-model insertion

**What:** Carry a context, drop a bare prompt, get **outcome-equivalent** results across substituted endpoints within a **stated confidence band**.

**Mechanism (prototype §16):** capability-aware payload shaping; output contracts; verification loop on oracle-bearing classes.

### Explicit non-claim (MUST appear in public copy)

> **Not achievable, and must never be implied: identical or near-identical output text.** Different models have different idioms. The product claims **task-outcome equivalence within a measured band** on classes with a verifiable oracle. Classes where the band is too wide are marked not substitutable; the router declines to hop inside them.

**Do not describe Pillar 2 to users until bands are measured** (prototype §18).

**Depends on:** Track B M1 hop-safety + Track C Tier 4.

---

## Pillar 3 — Managed capability graph / fleet probes

**What:** Aggregate, anonymized, **opt-in** probe data across the fleet. An individual cannot afford models × classes × repetitions at significance; a fleet can; marginal cost per user falls as the fleet grows.

**This is the clearest legitimate network effect in the product, and the pillar most likely to justify recurring revenue on its own.**

**Constraints (Appendix A.4):**

- Per-provider terms on automated benchmarking and comparative publication — managed graph may redistribute only what terms allow
- Cards stay priors; fleet data still does **not** become a public leaderboard rank
- Opt-in, anonymized; user can stay on local-only graph forever (free)

**Depends on:** Track C Probe + Graph planes at fleet scale; legal review of provider terms before redistribution.

---

## Pillar 4 — Enterprise governance

**What:** Budget envelopes per user, project, and task class — **enforcement**, not reporting. Policy routing as an enforced constraint (data classification → eligible endpoint set, so "this repo never leaves local inference" is a routing rule). Complete audit trail: model, context digest, cost, outcome per request. Data-residency-aware filtering. SSO and RBAC.

**Depends on:** Track C envelopes + persisted `RouteDecision`.

**Narrative:** see [ENTERPRISE.md](ENTERPRISE.md).

---

## Pillar 5 — Team / organizational shared memory

**What:** Shared context graphs scoped to a project. Onboarding transfers accumulated decision context, not a repository URL.

**Depends on:** Pillar 1. Most valuable to large teams.

---

## Pricing posture (prototype §5.3)

| Tier | Posture |
|---|---|
| Individual paid | Priced against **measurable routing savings** the Observatory already computes (falsifiable vs single-model baseline). Managed graph bundled. |
| Enterprise | Per seat with governance and support. Managed graph bundled. |

## Aggregator note

Pillars assume reachability plumbing (OpenRouter / LiteLLM / direct APIs) already exists. comPASS does not sell access aggregation; it sells the decision layer and portable memory on top (see [POSITIONING.md](POSITIONING.md)).
