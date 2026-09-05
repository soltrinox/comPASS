---
name: comPASS Track E — Product & GTM
overview: Positioning, free vs paid five pillars, enterprise value, open naming and working-copy decisions.
todos:
  - id: positioning-vs-aggregators
    content: "Write positioning vs OpenRouter, Hugging Face, Cursor auto-select, LiteLLM, and eval vendors"
    status: completed
  - id: free-tier-scope
    content: "Write free-tier scope: local engine, Observatory, advisory, local routing, local probes, bundle format + manual export/import; never paywall accuracy"
    status: completed
  - id: five-paid-pillars
    content: "Write five paid pillars: (1) cross-machine migration (2) multi-model insertion with outcome-equivalence band (3) managed capability graph / fleet probes (4) enterprise governance (5) team shared memory"
    status: completed
  - id: enterprise-governance
    content: "Write enterprise governance narrative for Finance, Security/compliance, and Engineering leadership buyers"
    status: completed
  - id: name-decision-record
    content: "ADR: product name (comPASS placeholder vs MODEL-GRAPH / ROUTE-GRAPH / ENI6MA-namespaced) before public remote — Proposed keep-comPASS / compass-router; awaiting Rosario confirmation"
    status: in-progress
  - id: working-copy-disposition
    content: "ADR: CHAT-COMPRESSOR 0.1.3 untracked tree — delete vs re-point at canonical comPREssOR 0.2.0"
    status: completed
  - id: gtm-one-pager
    content: "GTM one-pager: wedge, free/paid, non-claims, managed-graph as recurring-revenue justification"
    status: completed
isProject: false
---

# comPASS Track E — Product & GTM

## Purpose

Lock **positioning, packaging, and the two decisions that unblock a public repo** (name, working-copy disposition). This track is GTM and decision records. `isProject: false`. No compressor source edits. No engine scaffolding (Track C). Docs land under `/Users/rosario/work/comPASS/docs/gtm/` unless a file is an ADR that must live next to the repo root.

**Ground truth:** `/Users/rosario/work/comPASS/PROTOTYPE.md` Part I (§1–§8), §16 equivalence, Appendix A.  
**Summary:** `/Users/rosario/work/comPASS/SUMMARY/2026-09-03-comPASS-prototype-session.md`.

## Deliverable paths

```
/Users/rosario/work/comPASS/docs/gtm/
  README.md
  POSITIONING.md
  FREE-TIER.md
  PAID-PILLARS.md
  ENTERPRISE.md
  GTM-ONE-PAGER.md
/Users/rosario/work/comPASS/docs/adr/
  0001-product-name.md
  0002-working-copy-disposition.md
```

---

## 1) Positioning vs OpenRouter / HF / Cursor

File: `docs/gtm/POSITIONING.md`

Hold this distinction in every public sentence: **aggregators answer "can I reach it"; comPASS answers "should I use it, for this, at this budget."**

| Incumbent | They solve | They do not | comPASS posture |
|---|---|---|---|
| **OpenRouter** (and access aggregators) | Reachability + unified billing across many endpoints | Per-user capability posterior; session memory | **Consume** as catalog source + probe/execution substrate (§11.2). Complementary, not a replacement |
| **Hugging Face Hub** | Cards, weights, community evals | Operational routing against *this user's* task mix | Cards → **priors only**. Never override observations |
| **Cursor bundled auto-select** | Convenient IDE routing | Transparency, portability, user's budget/task mix | Transparent *why*; portable across tools; tuned to measured individual outcomes |
| **LiteLLM / gateways** | Protocol translation, retries, keys | Decision layer | **Reuse** as plumbing. Do not rebuild |
| **Eval vendors / public leaderboards** | Generic offline scores | Online private loop; decision wiring | Online, private, closes the loop. No published aggregate rank from our probes |

**Wedge, stated plainly:** personal ground truth **plus** portable memory. Neither half is separately defensible for long; together they are, because the corpus and the flywheel accrue to whoever holds both.

The compressor is why portable memory exists: forward payload is discrete text; hop cost is `CHAT_COMPRESSOR_FORWARD_BUDGET`, not transcript length. Tiers 1–3 resemble products that already exist; **Tier 4 does not**.

### Acceptance

Table present; "consume OpenRouter / reuse LiteLLM" explicit; no claim that we replace HF or Cursor.

---

## 2) Free-tier scope

File: `docs/gtm/FREE-TIER.md`

**Principle:** the free tier must be genuinely useful and must **never withhold correctness**. Anything required for the router to give *safe* answers stays free. Paid sells marginal cost and network effects.

### In the free tier (local, open source, single machine, single user)

- Full Observatory: catalog ingest, price/latency, drift detection, for endpoints the user can already reach
- Local task classification and local capability graph
- Advisory recommendations through the compressor injection surface (CC-9)
- Local routing for **owned** call sites: SDK wrapper and local proxy
- Local probe execution against the user's own corpus, on the user's own keys and budget
- The full portable-state-bundle **format**, plus **manual** export and import — file movement is free
- Single machine, single user, local persistence

### Explicitly not free (automated / fleet / org)

- Automated cross-machine sync (Pillar 1)
- Managed multi-model insertion as a service (Pillar 2)
- Fleet-aggregated managed capability graph (Pillar 3)
- Org-enforced governance (Pillar 4)
- Shared project memory (Pillar 5)

### Anti-pattern

**Do not paywall accuracy.** If free routes *worse* rather than *less conveniently*, trust dies and the free corpus that paid is built from dies with it.

### Confirm (Appendix A.5)

Bundle format + manual export/import stays free; only automated sync is paid. Write this as a closed decision in FREE-TIER.md unless product leadership objects — if objected, leave open and do not contradict PAID-PILLARS.md.

### Acceptance

A reader can list what is free vs paid without reading the prototype. Accuracy-not-paywalled is a bolded rule.

---

## 3) Five paid pillars

File: `docs/gtm/PAID-PILLARS.md`

Each pillar: what it is, why it is hard to self-host, what Track B/C work it depends on, honest scope.

### Pillar 1 — Cross-machine context migration

The context graph, the quantized tensor index, the state lineage, and the per-recipient injection ledger travel with the user across machines, encrypted end to end. Start on a laptop, continue on a workstation, resume from a cloud agent, lineage intact.

- Genuine marginal cost: storage, transfer, conflict resolution (prototype §15)
- Depends on Track B **CC-8** (bundle) and **CC-10** (quantization; index is **not** quantized today — float32 safetensors)
- Conflict: two machines advancing the same `agent_id` → branch at graph level (union + supersession), **not** last-write-wins on tensors. First release may present divergence as a user choice
- Manual export/import of the same format remains free

### Pillar 2 — Multi-model insertion

Carry a context, drop a bare prompt, get **outcome-equivalent** results across substituted endpoints within a **stated confidence band**.

**Mechanism (§16):** capability-aware payload shaping; output contracts; verification loop on oracle-bearing classes.

**Explicit non-claim (MUST appear in this doc and the one-pager):**

> Not achievable, and must never be implied: identical or near-identical output text. Different models have different idioms. The product claims **task-outcome equivalence within a measured band** on classes with a verifiable oracle. Classes where the band is too wide are marked not substitutable; the router declines to hop inside them.

Do not describe Pillar 2 to users until bands are measured (prototype §18).

Depends on Track B M1 hop-safety + Track C Tier 4.

### Pillar 3 — Managed capability graph / fleet probes

Aggregate, anonymized, **opt-in** probe data across the fleet. An individual cannot afford models × classes × repetitions at significance; a fleet can; marginal cost per user falls as the fleet grows.

**This is the clearest legitimate network effect in the product, and the pillar most likely to justify recurring revenue on its own.**

Constraints:

- Per-provider terms on automated benchmarking and comparative publication (Appendix A.4) — managed graph may redistribute only what terms allow
- Cards stay priors; fleet data still does not become a public leaderboard rank
- Opt-in, anonymized; user can stay on local-only graph forever (free)

### Pillar 4 — Enterprise governance

Budget envelopes per user, project, and task class — **enforcement**, not reporting. Policy routing as an enforced constraint (data classification → eligible endpoint set, so "this repo never leaves local inference" is a routing rule). Complete audit trail: model, context digest, cost, outcome per request. Data-residency-aware filtering. SSO and RBAC.

Depends on Track C envelopes + persisted `RouteDecision`.

### Pillar 5 — Team / organizational shared memory

Shared context graphs scoped to a project. Onboarding transfers accumulated decision context, not a repository URL. Depends on Pillar 1. Most valuable to large teams.

### Recurring-revenue justification

Lead with **Pillar 3 (managed graph)** as the subscription why: ongoing probe spend, ongoing drift, ongoing catalog churn. Pillars 1/5 are storage+sync. Pillar 4 is seat+support. Pillar 2 is a measured capability, not a vibe.

Pricing posture (prototype §5.3): individual paid tier priced against **measurable routing savings** the Observatory already computes (falsifiable vs single-model baseline). Enterprise per seat with governance and support. Managed graph bundled into both.

### Acceptance

All five pillars named and scoped. Pillar 2 non-claim on identical text is unmistakable. Pillar 3 called out as recurring-revenue core.

---

## 4) Enterprise governance narrative

File: `docs/gtm/ENTERPRISE.md`

Three distinct buyers (prototype §6.2):

**Finance.** Spend attribution per project, team, and task class, replacing one opaque invoice. Enforced budget envelopes. Savings quantified against a documented single-model baseline.

**Security and compliance.** Data classification drives endpoint eligibility, enforced at the routing layer. Auditable record of which endpoint received which context digest. Local-only routing for regulated work. Residency-aware filtering. Reduced concentration risk in a single external provider.

**Engineering leadership.** Faster onboarding through portable project context (Pillar 5). Measured rather than anecdotal model decisions. **Procurement leverage:** an org that can demonstrate per-task equivalence between two vendors and switch with bounded effort negotiates from a different position. That leverage may exceed direct routing savings for a large buyer.

Also state individual-practitioner value (§6.1) in a short preamble so the one-pager can steal it: lower cost at equal/better quality; less time lost to under-provisioned hard turns; continuity across machines; new endpoints evaluated on *their* work in days, not guessed from a leaderboard.

### Acceptance

Three-buyer structure; procurement-leverage paragraph present; no "we lock you in" language.

---

## 5) Name decision record

File: `docs/adr/0001-product-name.md`

**Status:** proposed (close before creating the public remote).

**Context:** `comPASS` is a placeholder chosen to match `comPREssOR` house style. Remote name is awkward to change later.

**Options:**

1. Keep `comPASS` / package `compass-router`
2. `MODEL-GRAPH` (descriptive)
3. `ROUTE-GRAPH`
4. ENI6MA-namespaced name if this sits in that portfolio (also tick Appendix A.6 registry)

**Decision needed from:** product owner (Rosario). This ADR records the choice and the date. Do **not** invent a rename in Track C CI.

**Consequences:** GitHub repo name, PyPI name, WASM artifact prefix, marketing one-pager header.

Until closed, all tracks keep using `comPASS`.

---

## 6) Working-copy disposition decision

File: `docs/adr/0002-working-copy-disposition.md`

**Status:** proposed (close before any compressor edit).

**Facts (from prototype §17.1, verified in-spec):**

- `/Users/rosario/work/CHAT-COMPRESSOR` is **not a git repository** (`git rev-parse` fails) and engine is **0.1.3**
- Canonical: `/Users/rosario/work/comPREssOR`, `git@github.com:soltrinox/comPREssOR.git`, branch `main`, engine **0.2.0**, clean tree
- Related distro: `soltrinox/OPENCLAW-comPREssOR`
- Three-file divergence: `hook_cli.py` differs mainly by version stamp; `graph.py` and `live_models.py` differ because canonical **removed hardcoded personal identifiers**
  - working copy: `FORBIDDEN_WORKSPACE = Path("/Users/rosario/work")`
  - canonical: generic project-root guard; identifier regex drops `rosario`

Canonical 0.2.0 is a **sanitized public-release line**, not a stale one.

**Options:**

1. Delete `/Users/rosario/work/CHAT-COMPRESSOR` after confirming no unique uncommitted work
2. Re-point it as a checkout of the canonical remote (replace contents; do not merge 0.1.3 identifiers forward)

**Forbidden:** implement CC-* against the untracked 0.1.3 tree and port later.

**Decision needed from:** Rosario. Track B agents must refuse to edit CHAT-COMPRESSOR regardless.

---

## 7) GTM one-pager

File: `docs/gtm/GTM-ONE-PAGER.md`

Keep to ~1 page (print) / ~400–700 words. Structure:

1. **Headline:** Capability-routed model selection with portable session state
2. **Problem:** wrong model per task; switching is too expensive
3. **Wedge:** personal ground truth + portable memory (compressor)
4. **How it works (3 bullets):** Probe / Graph / Route; Tiers 1–4
5. **Free vs paid:** correctness free; five pillars paid; managed graph = subscription why
6. **Enterprise:** finance / security / eng-lead
7. **Non-claims:** not identical text; not solved hop-credit; not an OpenRouter replacement
8. **Ask:** design-partner for managed graph + hop-safe compressor (M1)

Tone: exposition — mechanism, observable outcome, scope boundary. No hype adjectives.

### Acceptance

One-pager does not contradict PAID-PILLARS.md. Identical-text non-claim present. Managed graph named as recurring-revenue justification.

---

## Open decisions this track owns (prototype Appendix A)

| # | Decision | Where it closes |
|---|---|---|
| 1 | Product name | `docs/adr/0001-product-name.md` + master todo `decision-name` |
| 2 | Working-copy disposition | `docs/adr/0002-working-copy-disposition.md` + master todo `decision-working-copy` |
| 3 | Aggregator dependency posture | subsection in POSITIONING.md or PAID-PILLARS.md |
| 4 | Managed-graph data terms | PAID-PILLARS.md Pillar 3 |
| 5 | Free-tier sync boundary | FREE-TIER.md |
| 6 | ENI6MA registry | 0001 or a short note in CHARTER |

## Out of scope

- Implementing Probe/Graph/Route
- Editing comPREssOR
- Publishing marketing that implies identical outputs
- Creating the public remote before ADR 0001 is `accepted`

## References

- Prototype §1–§8, §16, Appendix A
- Master plan locked defaults and open decisions
- Track A CHARTER.md (product facts this track packages for GTM)
