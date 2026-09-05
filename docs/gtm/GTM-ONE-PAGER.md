# comPASS — GTM one-pager

**Working name:** comPASS · **Package:** `compass-router` · Brand lock: [ADR 0001](../adr/0001-product-name.md) (proposed)

## Headline

Capability-routed model selection with portable session state.

## Problem

Hundreds of reachable endpoints; price and fitness diverge by task. Public leaderboards measure someone else's mix. Most users pick one model and overpay on easy turns while under-provisioning hard ones. Switching mid-session is usually too expensive because session state is provider-captive.

## Wedge

**Personal ground truth plus portable memory.** Measure capability on the user's own work; keep session state in a bounded, model-agnostic digest (via comPREssOR). Neither half is durable alone; together the corpus and flywheel accrue to whoever holds both. Tiers 1–3 resemble existing products; **Tier 4 (per-turn routing inside one session) does not.**

## How it works

1. **Probe** — measure endpoints on the user's task classes (bandit-allocated; never "test everything constantly").
2. **Graph** — bitemporal capability store; cards are priors, observations are posteriors; drift supersedes versions.
3. **Route** — classify → constrain → score `quality − λ·cost` → fail-open; advisory in IDE, enforcement at owned call sites; Tier 4 hops when hop-safe.

## Free vs paid

- **Free (local, single user):** full Observatory, local graph, advisory, local routing, local probes, bundle **format** + **manual** export/import. **Accuracy is never paywalled.**
- **Paid — five pillars:** (1) automated cross-machine migration (2) multi-model insertion (3) managed capability graph / fleet probes (4) enterprise governance (5) team shared memory.
- **Subscription why:** **Pillar 3 — managed graph** (ongoing probe spend, drift, catalog churn). Pillars 1/5 storage+sync; Pillar 4 seat+support; Pillar 2 measured capability.

## Enterprise (three buyers)

- **Finance** — attribution + enforced envelopes + falsifiable savings vs single-model baseline.
- **Security/compliance** — classification → eligible endpoints; audit of context digests; local-only / residency.
- **Engineering leadership** — portable project context; measured model choices; **procurement leverage** from bounded switching cost.

## Non-claims

- **Not identical text** across substituted models — only **task-outcome equivalence within a measured band** on oracle-bearing classes; wide bands → not substitutable.
- **Not solved hop-credit** — reward attribution across hops is open; we record enough to re-attribute later.
- **Not an OpenRouter replacement** — we consume aggregators for reachability; we answer "should I use it, for this, at this budget."

## Ask

Design partners for **managed capability graph (Pillar 3)** and **hop-safe compressor (M1 / CC-2..CC-5)** — validate fleet probe economics and mid-session routing before public Pillar 2 messaging.
