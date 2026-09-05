# comPASS Charter

**Product placeholder:** comPASS (sister to comPREssOR)  
**Ground truth:** [`../PROTOTYPE.md`](../PROTOTYPE.md)  
**Architecture:** [`ARCHITECTURE.md`](ARCHITECTURE.md)  
**Canonical compressor:** `soltrinox/comPREssOR` @ engine **0.2.0** — never implement against `CHAT-COMPRESSOR` (0.1.3)

This charter states the problem, wedge, shippable tiers, free vs paid boundary, non-claims, and falsifiable success metrics for comPASS. Implementation lives in Tracks B–D; product/GTM in Track E. Track A produces contracts only.

---

## 1. Problem

Endpoint price spans roughly **two orders of magnitude** per token. Quality does **not** track price monotonically per task. A mid-tier model often matches a frontier model on constrained code edits, structured extraction, and short summarization, and fails badly at multi-step planning or long-context synthesis. The optimal choice is a function of **task type**, not a global ranking — yet almost every user makes one global choice and lives with it.

The cost of mismatch is asymmetric and mostly invisible. Overpaying on an easy task is a slightly larger invoice. Under-provisioning a hard task wastes a turn, propagates a wrong assumption, and burns human recovery time. The second cost dominates and is never measured.

Public leaderboards are weak inputs to a routing decision:

- Their task mix is not the user's task mix.
- Contents leak into training corpora, so scores drift upward independently of capability (**contamination**).
- They report a scalar where the decision needs a **vector** — a model that leads on aggregate may rank mid-pack on the one axis the user depends on.

What a routing decision requires is a **posterior over the user's own task distribution**, produced by measuring endpoints against work drawn from the user's history.

Endpoint behavior also changes underneath a stable identifier (quantization, serving stack, safety layer, silent version rolls). Any scoring system that treats a model id as a stable entity averages observations across a behavior break. Detecting the break and partitioning evidence is a hard requirement.

Finally, **session state is captive**. Conventional state is provider-shaped: conversation handles, paid warm KV, proprietary reasoning traces. Switching means full transcript replay or abandoning context. Organizations additionally lack spend attribution, enforced data-classification routing, and audit of which model saw which context.

---

## 2. Wedge

**Personal ground truth** (probes from the user's own history) **plus portable memory** (the compressor forward payload is unconditionally discrete text). Neither half alone is long-term defensible; together they are, because the corpus and the flywheel accrue to whoever holds both.

The compressor's forward channel is discrete text (`SampledPayload(kind="text", ...)`). Session state is a bounded, model-agnostic digest. Switching models mid-session therefore costs the **forward budget** (default 1024 tokens via `CHAT_COMPRESSOR_FORWARD_BUDGET`), not transcript length. That is the structural reason comPASS is a sibling of comPREssOR rather than a standalone router.

Flywheel: more sessions → more graph → better-calibrated routing → better outcomes per dollar → more reason to keep the compressor running.

---

## 3. What ships (tiers 1–4)

Four capability tiers, each **independently shippable**, each strictly harder than the last (prototype §2):

| Tier | Name | What it does |
|---|---|---|
| **1** | **Observatory** | Live catalog: endpoints, price, latency p50/p95, context window, rate limits, availability, licence/data posture; canary drift on fixed ids. Useful with no routing. |
| **2** | **Advisor** | Task classification + surfaced (not enforced) recommendation with measured scores and cost. Only tier expressible inside Cursor Agent Chat (hooks have no model field). |
| **3** | **Router** | Real enforcement at owned call sites: SDK wrapper, OpenAI-compatible proxy, budget envelopes, policy constraints, escalation ladders. |
| **4** | **Session orchestrator** | Per-turn routing inside one continuous session (hop + `hop_legal`, capability-aware payload shaping). Differentiated; requires compressor CC-1–CC-10. |

Planes that implement these tiers (see [`ARCHITECTURE.md`](ARCHITECTURE.md)):

- **Probe** — daemon; credentials; **NEVER on the prompt path**.
- **Graph** — bitemporal capability store + bandit posterior.
- **Route** — hot path; classify → score → decide; **fail-open**.

Scoring: `score(m, c) = E[quality(m, c)] − λ · E[cost(m, c)]`. Bandits (Thompson / UCB) over `(TaskClass, ModelVersion)` arms.

---

## 4. Free vs paid boundary

**Principle:** the free tier must be genuinely useful and must **never withhold correctness**. Never paywall accuracy.

### Free (local engine, open source)

- Full Observatory for endpoints the user can already reach.
- Local task classification and local capability graph.
- Advisory recommendations (CC-9 file handoff).
- Local routing for owned call sites (SDK wrapper + local proxy).
- Local probes on the **user's own keys and budget**.
- Full portable-state-bundle **format** plus **manual** export/import.
- Single machine, single user, local persistence.

### Paid — five pillars

1. **Cross-machine sync** of compressed session state (graph + quantized tensor index + lineage), encrypted E2E.
2. **Multi-model insertion** — carried context + bare prompt → **outcome-equivalence band** across substituted endpoints (never identical text).
3. **Managed capability graph** — aggregate, anonymized, opt-in fleet probe data.
4. **Enterprise governance** — enforced budget envelopes, policy routing, audit, residency, SSO/RBAC.
5. **Team shared memory** — project-scoped shared context graphs (depends on pillar 1).

Individual paid pricing is positioned against **realized savings vs a single-model baseline** (Observatory computes this). Enterprise is per-seat with governance and support.

---

## 5. Non-claims

Stated so marketing and docs cannot overstate:

1. **Not identical output across models.** Equivalence is an **outcome-equivalence band** on oracle-bearing task classes. Never identical or near-identical text.
2. **Not solved cross-hop credit assignment.** Persist `RouteDecision` + recipient lineage for later re-attribution; do not claim solved credit.
3. **Not a replacement for OpenRouter / LiteLLM.** Consume them as catalog/execution substrate and gateway plumbing.
4. **In-Cursor Agent Chat is advisory only.** Hook return shapes have no model field; Tier 2 advice only inside Agent Chat.

Additional posture: do not publish aggregate leaderboards from private probes; every capability figure carries `n` and `ci95`.

---

## 6. Success metrics (falsifiable)

Restated from prototype §17.3 as product acceptance:

| Milestone | Exit (product language) |
|---|---|
| **M0** | Recipient identity round-trips through `StateNode.meta` and survives lineage reload; no machine-specific absolute paths introduced in compressor code. |
| **M1** | Scripted hop at turn 20 delivers full, unsuppressed, full-budget payload; no-hop session matches 0.2.0 token accounting. |
| **M2** | Catalog populated with priced, versioned entries; induced fingerprint change triggers supersession (not score overwrite). |
| **M3** | Recommendations appear in session context; corrupt/stale/missing advisory **provably does not block** Agent Chat (CC-9 fail-open). |
| **M4** | Enforced routing with persisted `RouteDecision`; bundle round-trips across two machines with unchanged `hot_set` / `typed_projection` on fixtures. |

Additional product metrics:

- **Realized savings** vs single-model baseline (Observatory).
- **Hop-turn payload correctness** (Track B M1).
- **Advisory fail-open proof** (CC-9).

---

## 7. Out of scope for v1

- Exhaustive probing of every endpoint (bandit pruning is mandatory).
- Publishing aggregate leaderboards from private probes.
- Automatic tensor-branch merge on sync conflict (first release presents divergence as a user choice).
- Implementing against `CHAT-COMPRESSOR` / engine 0.1.3.
- Widening `ctx-graph.v1` — capability data lives only in sibling `model-graph.v1.json`.

---

## References

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — planes, tiers, identity normalization
- [`../PROTOTYPE.md`](../PROTOTYPE.md) — full product and integration specification
- [`API.md`](API.md) — Route plane + advisory contracts
- [`INTEGRATION.md`](INTEGRATION.md) — compressor CC-* touchpoints (Track B owns code)
- [`RISKS.md`](RISKS.md) — risk register
