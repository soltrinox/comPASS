# comPASS — Capability-Routed Model Selection with Portable Session State

**Status:** Prototype specification (pre-implementation)
**Date:** 2026-09-03
**Working name:** `comPASS` (placeholder — see Appendix A)
**Sibling engine:** `comPREssOR` — `git@github.com:soltrinox/comPREssOR.git`, engine version `0.2.0`
**Document scope:** Product strategy and positioning (Part I); architecture, integration mechanism, and required compressor modifications (Part II)
**Voice:** Exposition — mechanism, observable outcome, scope boundary. Claims that are not yet measured are marked as such.

---

## 0. Executive summary

There are now hundreds of reachable language-model endpoints, differing by more than an order of magnitude in price and by large, task-dependent margins in quality. No user has reliable information about which endpoint is best for *their* work, because published leaderboards measure generic benchmarks on a generic task mix, and those benchmarks are increasingly contaminated by training exposure. The practical result is that most users pick one model and overpay on easy tasks while underperforming on hard ones.

comPASS is an engine that measures model capability against a task taxonomy derived from the user's own work, maintains that measurement as a bitemporal capability graph, and routes each request to the endpoint that maximizes expected quality subject to a budget constraint.

The reason to build it next to `comPREssOR` rather than standalone is specific and mechanical. The compressor's forward channel is unconditionally discrete text — the vocabulary bridge carries the comment *"Compact frozen decode table so Cursor SDK always receives discrete text"*, and every return from `sample_text` is a `SampledPayload(kind="text", ...)`. Session state is therefore not held in provider-specific conversation ids, warm KV cache, or proprietary reasoning traces. It is held in a bounded, model-agnostic digest that any text-in endpoint can consume.

That yields the one capability nobody else can currently offer: **the cost of switching models mid-session is bounded by the forward budget, not by transcript length.** Continuous work can move between endpoints turn by turn. Combined with a capability graph, this makes per-turn routing inside a single session possible — cheap model drafts, strong model reviews, long-context model does the wide read, local model handles anything touching secrets.

The product ships in two tiers. The free tier is a local, single-machine, open-source engine: observatory, task classification, advisory recommendations, and local routing for call sites the user owns. The paid tier adds the two things that are structurally hard to self-host — **cross-machine migration of compressed session state** (the context graph plus a quantized tensor index travelling with the user) and **multi-model insertion**, where a carried context plus a bare prompt produces outcome-equivalent results across substituted endpoints within a stated confidence band — plus fleet-scale probe data, and enterprise governance over budget, policy, and audit.

Two things in this document are deliberately marked as unresolved rather than glossed. Reward attribution across model hops is an open research problem, and the "same output regardless of model" claim is achievable only at the level of task outcome within a confidence band, never as identical text. Both are treated explicitly in §12 and §16.

---

# PART I — PRODUCT, STRATEGY, AND POSITIONING

## 1. The problem

### 1.1 Capability is dispersed and price is not correlated with fitness

Endpoint pricing spans roughly two orders of magnitude per token. Quality does not track price monotonically per task. A mid-tier model frequently matches a frontier model on constrained code edits, structured extraction, and short summarization, at a fraction of the cost. The same mid-tier model may fail badly at multi-step planning or long-context synthesis. The optimal choice is therefore a function of task type, not a global ranking — but almost every user makes a single global choice and lives with it.

The cost of that mismatch is asymmetric and mostly invisible. Overpaying on an easy task shows up as a slightly larger invoice. Under-provisioning a hard task shows up as a wasted turn, a wrong assumption propagated into later work, and human time spent recovering. The second cost dominates and is never measured.

### 1.2 Public evaluation does not answer the operational question

Published leaderboards report aggregate scores on fixed public suites. Three properties make them weak inputs to a routing decision. Their task mix is not the user's task mix. Their contents leak into training corpora over time, so scores drift upward independently of capability. And they report a scalar where the decision needs a vector — a model that leads on aggregate may rank mid-pack on the one axis the user actually depends on.

What a routing decision requires is a *posterior over the user's own task distribution*. That can only be produced by measuring endpoints against work drawn from the user's history.

### 1.3 Endpoint behavior changes underneath a stable identifier

Providers revise the model serving a fixed public id — quantization changes, serving-stack changes, safety-layer changes, silent version rolls. Any scoring system that treats a model id as a stable entity will average observations across a behavior break and report a number describing neither the old nor the new model. Detecting the break and correctly partitioning the evidence is a hard requirement, not a refinement.

### 1.4 Session state is captive, so switching is prohibitively expensive

Even a user who knows a different model would be better for the next turn usually cannot act on it. Conventional session state is provider-shaped: server-side conversation handles, cached attention state that is being paid for, provider-specific message envelopes, and increasingly opaque reasoning traces that a competitor cannot ingest. Switching means either replaying the full raw transcript at full token cost, or abandoning accumulated context.

This is the lock-in that makes per-task routing theoretical for most users, and it is exactly the constraint the compressor removes.

### 1.5 Organizations have no cost or policy control surface

At team scale the gaps compound. There is no per-project or per-task spend attribution, so nobody can say which workflows consume the budget. There is no mechanism to express "this repository must not send content to third-party endpoints" as an enforced routing constraint rather than a policy document. There is no audit record of which model saw which context. And single-vendor dependency removes all procurement leverage.

## 2. What the product is

Four capability tiers, each independently shippable, each strictly harder than the last.

**Tier 1 — Observatory.** A live, queryable model of the endpoint landscape: which endpoints exist, price per input and output token, measured latency distributions reported as p50 and p95 rather than means, context window, rate limits, observed availability, declared licence and data-handling posture. Plus drift detection on fixed ids. This tier is useful with no routing at all, and it is the part that corresponds to "constantly testing the public endpoints."

**Tier 2 — Advisor.** Task classification plus a recommendation, surfaced but not enforced: *"this resembles multi-file refactoring; across your last 40 tasks of this class, model X scored 0.82 at $0.11/task and model Y scored 0.85 at $0.94/task."* This is where the scores are validated cheaply, because wrong advice is immediately visible. It is also the only tier expressible inside Cursor Agent Chat, for reasons developed in §13.1.

**Tier 3 — Router.** Real enforcement at owned call sites. Adds the control surfaces that make it an operational tool rather than a dashboard: budget envelopes, policy constraints, escalation ladders, per-task-class cost ceilings.

**Tier 4 — Session orchestrator.** Per-turn routing inside one continuous session. This is the differentiated capability and the one that requires the compressor. Tiers 1–3 resemble products that already exist; Tier 4 does not.

## 3. Why the compressor is the structural advantage

Three assets compound here, and none is easily replicated by a standalone router.

**Portable session state.** Established in §0: the forward payload is bounded model-agnostic text, so a hop costs the forward budget (default 1024 tokens, per `CHAT_COMPRESSOR_FORWARD_BUDGET`) rather than the full transcript. A competitor without a compressor has to choose between full replay and context loss.

**A private, uncontaminated evaluation corpus.** The context graph already accumulates the user's real tasks, decisions, open items, and outcomes, with timestamps and lineage. That is a probe corpus matched to the user's actual distribution and, because it is private, structurally immune to benchmark contamination.

**An implicit reward signal nobody else can observe.** The graph tracks `OpenItem` state transitions and supersession. An answer followed shortly by supersession of the fact it asserted, or by an open item that stays open, is weak evidence of a weak answer. This signal is noisy and confounded — task difficulty and model quality are entangled, and a confidently wrong answer that is never challenged looks like success — but it exists only for someone holding both halves. §12.4 treats it with appropriate caution.

The flywheel: more sessions produce more graph, which produces better-calibrated routing, which produces better outcomes per dollar, which makes the compressor more valuable to run. Both halves get better from the same data.

## 4. Capability curvature and the expert-board thesis

The central modelling commitment is that **model capability is a vector, not a scalar.** Contemporary models are heterogeneous internally — mixture-of-experts routing, distinct post-training regimes for code versus prose versus tool use, differing reinforcement signals for multi-step behavior. The externally visible consequence is that a model has a *capability curvature*: it is strong along some axes and mediocre along others, and the shape differs between models with similar aggregate scores.

The axes worth measuring separately, because they dissociate in practice:

- **Language generation** — fluency, register control, long-form coherence.
- **Code generation** — syntactic correctness, API accuracy, idiom match to an existing codebase.
- **Code comprehension and localization** — finding the relevant site in a large unfamiliar tree.
- **Multi-step planning** — decomposition, ordering, holding a goal across many turns.
- **Agentic tool use** — correct tool selection, argument construction, recovery from tool error.
- **Recursion and iteration** — the specific ability to run a build-test-fix loop to convergence without oscillating. This is the axis most relevant to the SDLC pipelines already in this workspace and it is essentially absent from public leaderboards.
- **Long-context fidelity** — retrieval accuracy deep into a large window, which degrades very differently across models than the advertised window suggests.
- **Structured output fidelity** — schema-valid JSON, adherence to output contracts, which matters disproportionately for a router because it determines whether downstream automation survives a substitution.
- **Multimodal input and image generation** — separate axes, separate providers.
- **Refusal and safety posture** — over-refusal on legitimate security, cryptography, and red-team work is a real capability cost in this workspace specifically.
- **Latency profile** — p50 and p95 separately; tail latency governs interactive feel.

Two evidence sources populate this vector. **Model cards give priors**: declared architecture, parameter count, context window, training-data description, licence, intended use, provider-reported evaluations. Cards are cheap, cover the entire catalog, and are self-reported — they are priors, never conclusions. **Probes give posteriors**: measured behavior on the user's task classes, which correct the prior where it is wrong.

This structure is why the output is a capability vector per model version, and why routing is a per-axis argmax under a budget constraint rather than a lookup against a leaderboard rank.

## 5. Free and paid tiers

The tiering principle: **the free tier must be genuinely useful and must never withhold correctness.** Anything required for the router to give *safe* answers stays free. The paid tier sells capabilities with real marginal cost or real network effects.

### 5.1 Free tier — local engine, open source

- Full Observatory: catalog ingestion, price and latency tracking, drift detection, for endpoints the user can already reach.
- Local task classification and the local capability graph.
- Advisory recommendations through the compressor's existing injection surface.
- Local routing for owned call sites: SDK wrapper and local proxy.
- Local probe execution against the user's own corpus, on the user's own keys and budget.
- The full portable-state-bundle *format*, plus export and import — manual file movement is free. Only automated sync is paid.
- Single machine, single user, local persistence.

This is a complete product for an individual, and shipping it as such is deliberate: it builds the corpus, exposes the reward-signal problem to real usage, and establishes the bundle format as a standard before anyone is asked to pay.

### 5.2 Paid tier — five pillars

**Pillar 1 — Cross-machine context migration.** The context graph, the quantized tensor index, the state lineage, and the per-recipient injection ledger travel with the user across machines, encrypted end to end. Start on a laptop, continue on a workstation, resume from a cloud agent, with lineage intact. This has genuine marginal cost (storage, transfer, conflict resolution) and genuine difficulty (§15).

**Pillar 2 — Multi-model insertion.** Carry a context, drop a bare prompt, and get outcome-equivalent results across substituted endpoints within a stated confidence band. Mechanism: capability-aware payload shaping, output contracts, and a verification loop (§16). Scoped honestly — outcome equivalence within a band, never identical text.

**Pillar 3 — Managed capability graph.** Aggregate, anonymized, opt-in probe data across the fleet. An individual cannot afford to probe hundreds of endpoints across a dozen task classes with enough repetition for significance; a fleet can, and the marginal cost per user falls as the fleet grows. This is the clearest legitimate network effect in the product, and it is the pillar most likely to justify recurring revenue on its own.

**Pillar 4 — Enterprise governance.** Budget envelopes per user, project, and task class, with enforcement rather than reporting. Policy routing as an enforced constraint — data classification determines the eligible endpoint set, so "this repo never leaves local inference" becomes a routing rule. Complete audit trail of model, context digest, cost, and outcome per request. Data-residency-aware endpoint filtering. SSO and role-based administration.

**Pillar 5 — Team and organizational shared memory.** Shared context graphs scoped to a project, so onboarding transfers accumulated decision context rather than a repository URL. This depends on Pillar 1 and is the most valuable to large teams.

### 5.3 Pricing posture

Individual paid tier priced against measurable routing savings, which the Observatory already computes — the product can state realized savings against a single-model baseline, so the value claim is falsifiable rather than aspirational. Enterprise priced per seat with governance and support. Managed capability graph access bundled into both.

The anti-pattern to avoid: paywalling accuracy. If the free tier routes *worse* rather than *less conveniently*, the product loses the trust it depends on, and the free tier stops producing the corpus the paid tier is built from.

## 6. Value to end users and enterprise clients

### 6.1 Individual practitioner

Lower cost at equal or better quality, because easy turns stop going to expensive endpoints. Less time lost to under-provisioned hard turns, because task class determines the model rather than habit. Continuity across machines. Freedom from single-vendor dependence — when a new endpoint appears, the graph evaluates it against the user's own work within days instead of the user guessing from a leaderboard.

### 6.2 Enterprise — three distinct buyers

**Finance.** Spend attribution per project, team, and task class, replacing a single opaque invoice. Enforced budget envelopes rather than after-the-fact reporting. Savings quantified against a documented single-model baseline.

**Security and compliance.** Data classification drives endpoint eligibility, enforced at the routing layer. Auditable record of which endpoint received which context digest. Local-only routing for regulated or classified work. Residency-aware filtering. Reduced concentration risk in a single external provider.

**Engineering leadership.** Faster onboarding through portable project context. Measured rather than anecdotal model decisions. Procurement leverage — an organization that can demonstrate per-task equivalence between two vendors and switch between them with bounded effort negotiates from a materially different position. That leverage is under-appreciated and may exceed the direct routing savings for a large buyer.

## 7. Positioning

**Against access aggregators (OpenRouter and similar).** They solve reachability and billing across many endpoints — one key, one API, many models. They do not maintain a per-user capability posterior, and they hold no session memory. comPASS is complementary and should *consume* them as both a catalog source and an execution substrate (§11.2). The distinction to hold in messaging: aggregators answer "can I reach it," comPASS answers "should I use it, for this, at this budget."

**Against proxy and gateway libraries (LiteLLM and similar).** These are plumbing — protocol translation, retries, key management. comPASS needs a gateway and should reuse rather than rebuild one. The differentiation is the decision layer above it.

**Against bundled IDE auto-selection (including Cursor's own).** Convenient, closed, tuned to the vendor's aggregate cost model rather than the user's task mix and budget, and offering no portability. comPASS is transparent about *why* an endpoint was chosen, tuned to the individual's measured outcomes, and portable across tools.

**Against evaluation vendors.** Offline, generic, contaminated over time, and not wired to a decision. comPASS is online, private, and closes the loop.

**The wedge, stated plainly:** personal ground truth plus portable memory. Neither half is separately defensible for long; together they are, because the corpus and the flywheel accrue to whoever holds both.

## 8. Adoption path and honest risks

Sequence: advisory inside the IDE first (cheapest validation of score quality), then the SDK wrapper for real enforcement in scripts and pipelines, then the proxy for broad coverage, then paid sync and multi-model insertion once the bundle format has been exercised.

Risks that could invalidate the thesis, stated rather than buried:

- **Probe economics.** Cost scales as models × task classes × repetitions. Without aggressive bandit pruning (§12.3) this dominates any routing savings. This is the most likely failure mode.
- **Provider terms.** Some providers restrict automated benchmarking or comparative publication. This must be read per provider before a probe daemon is pointed at them, and it constrains what the managed graph may redistribute.
- **Reward attribution.** Unsolved (§12.4). If per-hop credit assignment cannot be made to work, Tier 4 degrades to Tier 3 with manual selection — still useful, materially less differentiated.
- **Bundled auto-selection improving.** If vendor routing becomes good enough for most users, the addressable market narrows to cost-sensitive and policy-constrained buyers. Portability and governance remain defensible; generic routing quality does not.
- **API churn.** Catalog ingestion is coupled to provider APIs that change without notice. This is an ongoing maintenance cost, not a one-time build.

---

# PART II — TECHNOLOGY AND IMPLEMENTATION

## 9. Architecture: three planes with hard boundaries

One engine, three planes, separated by explicit latency, credential, and failure boundaries. The separation is a correctness requirement, not an aesthetic preference.

### 9.1 Probe plane

A long-running daemon. Executes probes against endpoints, records observations, detects drift. Holds provider API credentials. **Never in a prompt path.**

The credential boundary is inherited from an existing invariant: `hook_cli.py` states *"Never requires CURSOR_API_KEY,"* and the hook contract records that `CURSOR_API_KEY` is never written to the managed env file. A probe daemon requires live provider credentials by definition. Therefore the probe plane must be a separate process from anything running in the compressor's hook path — which is the concrete technical reason comPASS is a sibling repository rather than a module inside `chat_compressor`.

### 9.2 Graph plane

The bitemporal capability store plus the bandit posterior. Consumes observations, exposes a scoring query. Latency budget in the low tens of milliseconds for reads, because the route plane blocks on it. SQLite plus JSON documents, mirroring the compressor's existing two-tier pattern (`StateStore` uses SQLite for metadata and mmap-backed safetensors for tensors) so operational knowledge transfers.

### 9.3 Route plane

The only component in the hot path. Classifies the request, queries the graph, returns an endpoint decision. Hard requirements: bounded latency (target p95 under 50 ms), and **fail-open to a configured default on any error.** The compressor already demonstrates the discipline to copy — every hook handler catches broadly, logs, and returns the event-safe default so Agent Chat is never blocked. The router must never be the reason a request fails.

### 9.4 Stack

Python 3.11+, matching the compressor's `requires-python`. SQLite for metadata; JSON for graph documents; safetensors for tensor payloads. NumPy for scoring. No mandatory heavyweight dependency in the route plane — the probe plane may depend on more, since it is not latency-bound. Optional-dependency groups mirror the compressor's `[project.optional-dependencies]` layout (`dev`, `hf`, `sdk`).

## 10. The capability graph schema

### 10.1 Why not reuse `ctx-graph.v1`

The context graph's node kinds are fixed at `("Turn", "Topic", "Fact", "OpenItem", "Event")` and its relations at `("mentions", "contains", "continues", "supersedes", "derived_from")`, enforced by both the JSON schema `enum` and an explicit `ValueError` in `CtxGraph.add_edge`. A capability graph needs entirely different entities. Widening those enums would degrade both schemas and break validation of existing artifacts. A sibling schema, `model-graph.v1.json`, is the correct move.

### 10.2 What to borrow: bitemporality

Every `ctx-graph.v1` node carries `valid_start`, `valid_end`, and `status` in `("active", "superseded", "deprecated")`, and `CtxGraph.supersede` closes the old interval while opening a new node and adding a `supersedes` edge.

That pattern is unusually well matched to §1.3. When probes detect a behavior break at a fixed model id, the correct representation is not overwriting a score — it is superseding the `ModelVersion` and opening a new validity interval, so subsequent scoring queries filter by interval and never average across the break. Reusing this pattern means drift handling is close to free, and it is the single highest-value piece of design transfer between the two projects.

### 10.3 Node and edge kinds

Nodes: `Provider`, `Model`, `ModelVersion`, `TaskClass`, `CapabilityAxis`, `Probe`, `Observation`, `PriceQuote`, `Policy`, `RouteDecision`.

Edges: `serves` (Provider → ModelVersion), `version_of` (ModelVersion → Model), `measures` (Probe → CapabilityAxis), `observed_on` (Observation → ModelVersion), `evidences` (Observation → Probe), `priced_by` (PriceQuote → ModelVersion), `supersedes`, `derived_from`, `constrains` (Policy → ModelVersion), `selected` (RouteDecision → ModelVersion).

Sketch:

```json
{
  "schema": "model-graph/v1",
  "nodes": [
    {
      "id": "urn:mg:modelversion:8f2c1d",
      "kind": "ModelVersion",
      "label": "cursor-grok-4.6-high-fast@2026-08-14",
      "status": "active",
      "valid_start": "2026-08-14T00:00:00Z",
      "valid_end": null,
      "attrs": {
        "model_id": "cursor-grok-4.6-high-fast",
        "provider": "cursor",
        "context_window": 262144,
        "tokenizer_id": "unknown",
        "price_in_per_mtok": 0.0,
        "price_out_per_mtok": 0.0,
        "card_source": "cursor:models.list",
        "drift_fingerprint": "cn_4a91f0",
        "capability": {
          "code_generation":  {"mean": 0.81, "n": 42, "ci95": 0.06},
          "multi_step_plan":  {"mean": 0.74, "n": 18, "ci95": 0.11},
          "recursion_loop":   {"mean": 0.69, "n": 9,  "ci95": 0.19},
          "structured_output":{"mean": 0.94, "n": 51, "ci95": 0.03}
        }
      }
    }
  ],
  "edges": []
}
```

Two schema commitments worth stating. Every capability figure carries `n` and a confidence interval, never a bare mean — the router must be able to distinguish "measured as mediocre" from "barely measured," because those imply different actions (route away versus probe more). And `RouteDecision` nodes are persisted, making every routing choice auditable after the fact and providing the join key for retroactive reward re-attribution (§12.4).

## 11. Ingestion: model cards and aggregator platforms

### 11.1 Hugging Face Hub

The richest structured source for open models. Useful surfaces: the model card (`README.md` front matter — declared task tags, licence, base model, language coverage), `config.json` (architecture, hidden size, layer count, MoE expert count where present), `tokenizer_config.json` (tokenizer family, vocabulary size, special tokens — directly relevant to §14, CC-6), and hub metadata (download counts, likes, last modified) as weak popularity priors.

Cards map to **priors over capability axes**, never to scores. Declared task tags and architecture set an initial belief; probes move it. The honesty constraint: card evaluations are self-reported, frequently stale, and selectively presented. They are recorded with `card_source` provenance and are never allowed to override an observation.

### 11.2 OpenRouter and access aggregators

Aggregators are the highest-leverage ingestion source because they normalize what is otherwise per-provider bespoke work: a unified catalog across many providers, comparable per-token pricing, published throughput and latency, availability signals, and one credential for probe execution. Consuming an aggregator both populates the Observatory and provides the execution substrate for the probe plane, which collapses a large amount of integration work.

### 11.3 Cursor

Cursor exposes a model list, and the compressor already has working normalization code for it: `extract_model_ids` handles the `ListResult`/dict/iterable/`SDKModel` variants, and `resolve_model_ids` maps requested arms onto available ids with documented alias fallbacks and an explicit `missing` list. Both are directly reusable — this is the second concrete piece of code transfer, alongside the bitemporal pattern.

### 11.4 The identity normalization problem

The same underlying model appears under different ids across platforms, with different quantization, different serving stacks, and different effective context windows. Naive id-keyed merging will conflate genuinely different endpoints; naive splitting will fragment evidence and starve every cell of samples.

Resolution: treat `(provider, served_id)` as the identity of a `ModelVersion`, and link versions to a shared `Model` node via `version_of` only when a behavioral fingerprint agrees. Fingerprints come from a small fixed canary probe set (§12.5). Evidence pools at the `Model` level as a prior and is measured at the `ModelVersion` level as a posterior.

## 12. Probing and scoring

### 12.1 Probe corpus from the user's own history

Probes are drawn from the user's context graphs, not from public suites. The graph already extracts `Fact` nodes with a `kind_hint` of `decision`, `design`, or `outcome`, `OpenItem` nodes with open/deferred/done state, and `Event` nodes for outcomes. A probe is a task reconstructed from a real historical episode where the outcome is known — which gives task-distribution match and contamination immunity in one move.

### 12.2 Task taxonomy

The classifier maps an incoming request to a `TaskClass`. Classes are derived by clustering historical episodes, seeded with the axes in §4. Features reuse existing compressor machinery — `extractive.keyword_set`, `chunks.chunk_text`, `rank.rank_chunks` — rather than a new featurizer.

Two properties govern the design. Classification must happen *before* the answer is known, from the prompt and the current graph state alone. And misclassification cost is asymmetric: routing a hard task to a weak model wastes a turn plus human recovery time, while the reverse wastes a few cents. The policy is therefore deliberately biased toward over-provisioning, with mid-turn escalation (§13.3) as the recovery path.

### 12.3 Allocation: bandits, not exhaustive probing

"Constantly testing every endpoint" is the failure mode identified in §8. Treat `(TaskClass, ModelVersion)` as bandit arms and allocate probe spend by Thompson sampling over the posterior. Spend concentrates where a cell is either promising or genuinely uncertain, and falls to near zero on cells already established as poor. Because nondeterminism requires n > 1 per cell, cost scales as models × classes × repetitions and pruning is mandatory rather than an optimization.

For the routing decision itself, avoid solving a constrained optimization per request. Score each candidate as:

```
score(m, c) = E[quality(m, c)] − λ · E[cost(m, c)]
```

and tune the single scalar λ in a slow outer loop until realized spend meets the target rate. This is the Lagrangian relaxation of the budget constraint: a few lines of code, one interpretable knob, and graceful degradation when the estimate is wrong.

### 12.4 The reward signal — three sources, one open problem

**Verifiable outcomes (strongest).** Tests pass, code compiles, schema validates, output matches a known answer. Honest, cheap, automatic. Limitation: only covers task classes with a checkable oracle, so the graph is well-calibrated on code and structured output and comparatively blind on synthesis and long-form reasoning.

**Implicit signals from the compressor (unique, noisy).** `OpenItem` nodes that stay open, `Fact` nodes superseded shortly after assertion, users re-asking. `CtxGraph.openitem_signature()` and `supersede_count()` already expose exactly these transitions, and `sample_for` already reads them each turn. This is the signal only a holder of both halves can observe. It is also confounded — difficulty and quality are entangled, and a confidently wrong answer that is never challenged reads as success — so it is used as a weak prior with explicit uncertainty, never as a primary reward.

**Model-as-judge (broad, biased).** Covers everything else at the cost of money, latency, and an unauditable bias including self-preference when judge and candidate are related. Used only where the first two are unavailable, and always recorded with the judge's identity so its contribution can be discounted later.

**The open problem: credit assignment across hops.** If turn 8 goes to a cheap model and introduces a wrong assumption, and turn 12 on a strong model fails as a consequence, naive per-turn attribution blames the strong model and drives the router toward the wrong policy. Honest options are all unsatisfying: attribute to the whole trajectory (low signal), restrict to short episodes with verifiable endpoints (limits coverage), or counterfactual replay (expensive, valid only under determinism).

The design commitment is therefore to **record enough to re-attribute later rather than to fix attribution now.** Persisted `RouteDecision` nodes, per-turn recipient identity in the compressor's state lineage (§14, CC-1), and full context digests make retroactive re-scoring possible once the problem is better understood. This is explicitly an unsolved area and should not be presented to users as solved.

### 12.5 Drift detection

A small fixed canary probe set runs against every active `ModelVersion` on a schedule. Responses are fingerprinted; a fingerprint shift beyond a calibrated threshold triggers `supersede` on the `ModelVersion` and opens a new interval, so prior observations remain attached to the prior version. Canary probes are the only probes that run unconditionally, since drift detection cannot be bandit-pruned without defeating its purpose.

### 12.6 Statistical discipline

Repetition per cell with variance tracking. Paired comparison on identical inputs where possible, since between-model variance is much larger than within-model variance. Confidence gating — the router declines to prefer a candidate when intervals overlap, falling back to cost as the tiebreak. No aggregate leaderboard rank is published from these numbers; the existing `render_proof` output already ends with *"No winner is declared from these metrics alone,"* and that discipline carries forward.

## 13. Routing and enforcement

### 13.1 Three enforcement targets

**Advisory, inside Cursor.** The hook contract fixes the return shapes: `beforeSubmitPrompt` returns `{"continue": true}` and may add `additional_context`; `sessionStart` returns `{"additional_context": ""}`. There is no model field. A router integrated at this surface can only *advise* — inject a recommendation line and let the human or agent act. This is a genuine product (Tier 2) but it is not enforcement, and the documentation must not overstate it.

**Cursor SDK wrapper.** Anything constructing an agent with an explicit model parameter can be routed for real. This is the first target with actual enforcement and the right place to aim first.

**OpenAI-compatible proxy.** A local endpoint accepting chat-completion requests, classifying, selecting, and forwarding. Broadest coverage, owns provider credentials, and therefore lives strictly in the probe/route service process, never in the hook path.

### 13.2 Decision procedure

Classify to a `TaskClass`. Filter candidates by hard constraints — policy, data classification, context-window sufficiency, availability. Score survivors by `quality − λ·cost`. Apply confidence gating; on overlapping intervals prefer lower cost. Check the budget envelope and downgrade if the envelope is exhausted. Persist a `RouteDecision`. Return the choice with a machine-readable rationale.

### 13.3 Escalation ladder

For task classes where failure is cheaply detectable, attempt a cheap candidate first, detect failure by the verifiable signal, and retry on a stronger candidate. Expected cost is lower than always-strong whenever the cheap model's success rate exceeds roughly the cost ratio. This is only sound where failure detection is reliable — applying it to unverifiable tasks silently ships bad output, so it is gated on task class having an oracle.

### 13.4 Budget envelopes

Envelopes attach at session, project, and organization scope with a period and a limit. The route plane consults the envelope, raising λ as consumption approaches the limit so degradation is gradual rather than a hard stop. Enforcement, not reporting, is the paid-tier differentiator (§5.2, Pillar 4).

## 14. Required compressor modifications

This is the integration core. All changes target the canonical repository `soltrinox/comPREssOR` (engine `0.2.0`, branch `main`). A scan of `engine/src/chat_compressor/` confirms there is currently **no model or recipient awareness anywhere in the engine** — the only matches for model-related identifiers are in `live_models.py`, which handles A/B arm resolution, not per-turn recipient tracking. All defects below are live in `0.2.0`.

### 14.1 Three latent defects that model-hopping exposes

These are the priority, because they fail *silently* — a hopped session degrades without any error surfacing.

**CC-1 — State lineage does not record the recipient.** `PersistentAgentHandle.step` persists `meta={"tool_status": "stub", "tokenizer_id": "hashed-ngram"}`. Nothing records which model produced or consumed a turn. This is the root cause of the next three defects and a prerequisite for reward attribution (§12.4). *Change:* add `recipient_id`, `recipient_version`, and `route_decision_id` to `StateNode.meta`. Additive, backward compatible, small.

**CC-2 — Dedup suppression assumes a fixed recipient.** `sample_for` builds a suppression set via `recent_line_hashes(history, k=3)` from `load_inject_history(self._agent_dir())` — keyed per *session*, not per recipient. `pack_forward` then drops any line whose hash is in that set. A newly swapped-in model never saw those lines, so it receives a payload with holes precisely where the system decided the content was already known. *Change:* partition the inject ledger by `recipient_id`.

**CC-3 — Dedup must reset on recipient change.** `pack_forward` already clears the suppression set entirely when `node_superseded` is true (`if node_superseded or not cross_turn_dedup_enabled(): suppress = set()`). That is exactly the needed precedent. *Change:* add recipient change as a third reset trigger alongside supersession.

**CC-4 — The skip path can send a new model nothing at all.** `pack_forward` returns an empty payload with `method="skip"` when `allow_skip and not openitem_changed and not node_superseded and packed < skip_floor_tokens`. For a model already in the conversation this is correct and is where token savings come from. For a model that has just arrived it is catastrophic: it starts with zero context and no signal that anything is missing. *Change:* gate `allow_skip` on recipient continuity — never skip on a recipient's first turn.

**CC-5 — Adaptive budget starves late-joining models.** `adaptive_budget(t, novelty_rate)` returns the full budget for `t <= WARMUP_TURNS` (3) and then scales down with rolling novelty. A model swapped in at turn 40 receives the turn-40 budget when it needs the turn-1 budget. *Change:* compute warmup against a per-recipient turn counter rather than the session `t`.

### 14.2 Capability and correctness additions

**CC-6 — Tokenizer-accurate cost estimation.** All budgeting flows through `estimate_tokens`, which is `max(1, (len(text) + 3) // 4)`. Reasonable for English on GPT-family BPE; it drifts materially on dense code, JSON, and non-Latin scripts, and it drifts *differently per tokenizer*. A product whose central claim is cost-efficiency cannot carry a systematic error of that size in the denominator. *Change:* introduce a pluggable token counter resolved per recipient, keeping the cheap estimate for internal packing and using an accurate count for cost decisions. Tokenizer identity is available from ingestion (§11.1).

**CC-7 — Hop legality gate.** `meta` records `tool_status: "stub"`, so tool state is explicitly unimplemented. A hop while a tool call is in flight has no defined semantics, and tool-call formats, parallel-call support, and reasoning-block handling differ per provider. *Change:* expose a `hop_legal()` predicate — legal only at turn boundaries with no pending tool state — and have the router respect it as a scheduling constraint.

**CC-8 — Portable state bundle export and import.** Prerequisite for paid Pillar 1. *Change:* add `export_bundle()` / `import_bundle()` producing and consuming the format in §15, with a round-trip equivalence test.

**CC-9 — Advisory injection surface.** The router needs a documented way to contribute a recommendation line to `additional_context` without coupling the hook path to the router process or its credentials. *Change:* an optional, fail-open, file-based handoff — the router service writes a small advisory document under the state root; `_compose_additional_context` includes it when fresh and ignores it when stale, missing, or malformed. Keeps the credential boundary of §9.1 intact.

**CC-10 — Quantized tensor index.** `StateStore.save` writes `float32` safetensors (`np.asarray(C, dtype=np.float32)`). For local mmap use this is fine. For cross-machine sync it is 4× larger than necessary. *Change:* optional `int8` or `fp16` quantization with the scheme recorded in `meta`, and a measured reconstruction-error budget. Note the correction to an earlier framing: the index is *not* currently quantized — quantization is new work, not an existing property.

### 14.3 Change summary

| ID | File | Change | Risk | Test |
|----|------|--------|------|------|
| CC-1 | `handle.py`, `store.py` | Recipient fields in `StateNode.meta` | Low — additive | Lineage round-trip preserves recipient |
| CC-2 | `handle.py`, `store.py` | Per-recipient inject ledger | Medium — changes dedup behavior | New recipient receives unsuppressed payload |
| CC-3 | `pack.py` | Recipient change resets suppression | Low — mirrors supersede path | Hop turn packs full content |
| CC-4 | `pack.py`, `handle.py` | Gate `allow_skip` on continuity | Low | First turn for a recipient never skips |
| CC-5 | `pack.py`, `handle.py` | Per-recipient warmup counter | Low | Late joiner gets full budget |
| CC-6 | new `tokens.py` | Pluggable token counter | Medium — touches budgeting | Counts match reference tokenizers |
| CC-7 | `handle.py` | `hop_legal()` predicate | Low — new API | Returns false with pending tool state |
| CC-8 | new `bundle.py` | Bundle export/import | Medium | Round-trip equivalence |
| CC-9 | `hook_cli.py` | Fail-open advisory inclusion | Low — must stay fail-open | Missing/stale/corrupt advisory does not block |
| CC-10 | `store.py` | Optional tensor quantization | Medium — numerical | Reconstruction error within budget |

### 14.4 Compatibility discipline

Every change is additive or gated by an environment knob, following the existing pattern where `CHAT_COMPRESSOR_CROSS_TURN_DEDUP` and `CHAT_COMPRESSOR_INJECT_P1` gate behavior with safe defaults. New knobs are documented in `engine/env.example` and in `docs/HOOK_CONTRACT.md` under managed keys. The fail-open invariant is non-negotiable: no change may introduce a path where a router or advisory failure blocks Agent Chat. `ctx-graph.v1` node and edge enums are not widened. Absent recipient information, every changed code path must behave exactly as `0.2.0` does today, so existing state directories keep working untouched.

## 15. Portable state bundle and cross-machine migration

### 15.1 Format

```
bundle.v1/
  manifest.json        # schema, version, producer id, d, k_max, tokenizer_id,
                       # quantization scheme, lineage head, checksums
  graph.json           # ctx-graph/v1 document
  states/
    t0001.safetensors  # C, M (+ KV), optionally quantized
    ...
  inject_ledger.json   # per-recipient injection history (CC-2)
  lineage.json         # state_id / parent_id / t chain with recipient per turn
```

### 15.2 Producer compatibility

The compressor's C matrices are produced by a specific embedding producer at a specific dimension. `StateStore` records `producer`, `d`, and `k_max` per agent and per state, and `meta` records `tokenizer_id`. A bundle is only directly loadable on a machine whose producer configuration matches. Where it does not, the options are re-projection through the existing vocabulary bridge or graph-only import with tensor state discarded. The manifest must carry enough information for the importer to decide and to report which mode it used — a silent mismatch that produces subtly wrong embeddings is the worst available outcome.

### 15.3 Quantization

Per CC-10, `fp32 → int8` reduces transfer by 4× at the cost of reconstruction error. Because the C matrices are L2-normalized (`append_then_pool` returns `l2_normalize(...)`), values are bounded and well-conditioned for symmetric per-row scaling. The acceptance criterion is behavioral rather than numerical: cosine similarity between original and reconstructed rows above a threshold, plus unchanged `hot_set` and `typed_projection` output on a fixture corpus.

### 15.4 Sync and conflicts

End-to-end encryption with client-held keys; the service stores ciphertext. Conflict arises when two machines advance the same `agent_id` independently, producing divergent lineage from a common parent. Since the graph is append-only and supersession is explicit, the sound resolution is to treat divergence as a branch and merge at the graph level — union of nodes, with supersession edges resolving contradictions — rather than last-write-wins on tensors, which would silently discard a turn. Merge semantics for the tensor chain are genuinely harder and the honest first release should present divergence to the user as a choice rather than guess.

## 16. Equivalence under substitution

Paid Pillar 2 promises that a carried context plus a bare prompt yields comparable results across substituted endpoints. This must be scoped precisely, or it becomes an unsupportable claim.

**Achievable:** *task-outcome* equivalence within a stated confidence band on task classes with a verifiable oracle. Test passes, schema validates, extraction matches, build converges. The band is measurable and reportable per task class.

**Not achievable, and must never be implied:** identical or near-identical output text. Different models have different idioms, and no amount of context engineering makes their prose converge.

**Mechanism.** Three components. *Capability-aware payload shaping* — the forward payload is adapted per recipient, since a model weak on long-context fidelity needs a tighter, more explicitly structured digest than one strong on it; the existing quota structure in `hot_set` (open-item, decision, and path/heading shares) is the natural place to vary this. *Output contracts* — where the task permits, the request specifies a schema, which collapses much cross-model variance and is measurable via the structured-output axis. *Verification loop* — for oracle-bearing classes, verify and escalate rather than trusting the substitution.

**Reporting.** Each task class carries a published equivalence band derived from paired probes. Classes where the band is too wide are marked as not substitutable, and the router declines to hop within them. Honest scoping here is what makes the claim defensible rather than marketing.

## 17. Repository and delivery plan

### 17.1 Repository facts to correct before any push

The working directory `/Users/rosario/work/CHAT-COMPRESSOR` is **not a git repository** — `git rev-parse` fails there — and its engine is version `0.1.3`. The canonical repository is `/Users/rosario/work/comPREssOR`, remote `git@github.com:soltrinox/comPREssOR.git`, branch `main`, engine version `0.2.0`, clean working tree. A related distribution exists at `soltrinox/OPENCLAW-comPREssOR`.

Three files differ between the trees, and the nature of the difference matters: `hook_cli.py` differs only in the version stamp, while `graph.py` and `live_models.py` differ because the canonical repository has **deliberately removed hardcoded personal identifiers** — `live_models.py` in the working copy defines `FORBIDDEN_WORKSPACE = Path("/Users/rosario/work")` and guards against it by absolute path, where canonical guards against project root generically; `graph.py`'s identifier regex drops `rosario` from its alternation. Canonical `0.2.0` is a sanitized public-release line, not a stale one.

Consequences: all CC-* changes target `comPREssOR`, and they must be written without machine-specific absolute paths so the sanitization is not silently reverted. Implementing against the untracked working copy and porting afterward would reintroduce exactly the identifiers that were removed for publication.

### 17.2 New sibling repository

Layout mirroring `comPREssOR/engine` so operational knowledge transfers:

```
comPASS/
  README.md
  PROTOTYPE.md            # this document
  pyproject.toml          # name: compass-router, requires-python >=3.11
  schema/
    model-graph.v1.json
    bundle.v1.json
  src/compass/
    graph.py              # bitemporal capability store
    ingest/               # huggingface.py, openrouter.py, cursor.py
    probe/                # corpus.py, runner.py, canary.py
    score/                # bandit.py, reward.py, drift.py
    route/                # classify.py, decide.py, envelope.py
    serve/                # proxy.py, advisory.py
    bundle.py             # bundle read/write (paired with compressor CC-8)
  scripts/                # test-*.sh, validate-*.sh (pattern-discovered)
  tests/
  test-results/
  docs/
```

Distribution follows the compressor's existing channels: a Python package, and the VS Code extension already published as `compressor-0.2.0.vsix` is the natural surface for the advisory UI.

### 17.3 Milestones with falsifiable exit criteria

**M0 — Consolidate and instrument.** Settle the working-copy disposition (Appendix A.2) so there is one authoritative tree. Land CC-1. *Exit:* recipient identity round-trips through `StateNode.meta` and survives lineage reload, with test evidence; no machine-specific absolute path introduced.

**M1 — Hop safety.** Land CC-2 through CC-5. *Exit:* a scripted session that switches recipient at turn 20 delivers a full, unsuppressed, full-budget payload on the hop turn; the same session without a hop shows unchanged token accounting versus `0.2.0` baseline. This milestone alone makes manual model-hopping correct and is independently valuable.

**M2 — Observatory.** `model-graph.v1.json`, ingestion from at least two sources, drift detection with canary probes. *Exit:* catalog populated with priced, versioned entries; an induced fingerprint change triggers supersession rather than score overwrite.

**M3 — Advisor.** Task classification, probe corpus from real history, bandit allocation, CC-9 advisory surface. *Exit:* recommendations appear in session context; a corrupt or stale advisory file provably does not block Agent Chat.

**M4 — Router and bundle.** SDK wrapper and proxy enforcement, budget envelopes, CC-8 and CC-10. *Exit:* enforced routing with persisted `RouteDecision` records; bundle round-trips across two machines with `hot_set` and `typed_projection` output unchanged.

## 18. Validation and proof obligations

Per the workspace SDLC constitution, each milestone produces log-backed evidence rather than assertions: timestamped `.log.txt` artifacts under `test-results/<topic>/`, a proof report linking every claim to a specific artifact, and re-run instructions. Claims are falsifiable as written — "recipient round-trips" is checkable from the log; "hopping works better" is not, and is not used.

The environment matrix for this project is local Python, local Docker (once a Dockerfile exists), the proxy service, and the IDE hook path, each graded FULL / PARTIAL / NOT_RUN from log evidence. The recursive build-test-fix loop applies with the standard bounded iteration limits.

Two obligations specific to this product. Any published capability number must carry `n` and a confidence interval, and no aggregate ranking is published from probe data — continuing the discipline already visible in `render_proof`. And the equivalence bands of §16 must be measured before Pillar 2 is described to users in any form.

---

## Appendix A — Open decisions

1. **Product name.** `comPASS` is a placeholder chosen to match the `comPREssOR` house style. Alternatives: `MODEL-GRAPH` (descriptive), `ROUTE-GRAPH`, or an ENI6MA-namespaced name if this is positioned inside that portfolio. Decide before repository creation, since the remote name is awkward to change later.
2. **Working-copy disposition.** `CHAT-COMPRESSOR` is untracked and behind (`0.1.3` vs `0.2.0`), and its divergence is the pre-sanitization variant (§17.1). Decide whether to delete it, or re-point it at the canonical remote as a checkout. Leaving an untracked near-duplicate in the workspace invites edits landing in the wrong tree.
3. **Aggregator dependency posture.** Whether OpenRouter is a hard dependency for probe execution or one interchangeable backend among several. Affects both cost model and vendor risk.
4. **Managed-graph data terms.** What may be aggregated from opt-in users and redistributed, given per-provider terms on benchmarking and comparative publication.
5. **Free-tier boundary on sync.** Confirm that bundle format plus manual export/import stays free and only automated sync is paid.
6. **ENI6MA registry.** Whether this project is ENI6MA-derived and therefore requires an entry under `ENI6MA-REGISTRY/projects/`.

## Appendix B — Glossary

**Capability curvature** — the per-axis shape of a model's ability, as opposed to a scalar rank.
**Task class** — a cluster of user requests sharing a routing decision, derived from history.
**Recipient** — the specific model version consuming a forward payload on a given turn.
**Hop** — a recipient change within one continuous session.
**Forward payload** — the packed `HOT_SET` → typed lines → ranked chunks text the compressor injects, bounded by `CHAT_COMPRESSOR_FORWARD_BUDGET`.
**Bundle** — the portable serialization of graph, tensor index, lineage, and inject ledger.
**Equivalence band** — the measured confidence interval within which substituted models produce equivalent task outcomes for a task class.
**Envelope** — a scoped spend limit enforced at routing time.

## Appendix C — Reference map

| Path (in `comPREssOR/engine`) | Role in this integration |
|---|---|
| `src/chat_compressor/handle.py` | `sample_for` / `step`; primary site for CC-1, CC-2, CC-5, CC-7 |
| `src/chat_compressor/pack.py` | `pack_forward`, `adaptive_budget`; site for CC-3, CC-4, CC-5 |
| `src/chat_compressor/store.py` | `StateStore`, inject ledger helpers; site for CC-1, CC-2, CC-10 |
| `src/chat_compressor/graph.py` | `CtxGraph`, supersession, `hot_set`; bitemporal pattern to borrow; reward signals |
| `src/chat_compressor/hook_cli.py` | Hook events and fail-open defaults; site for CC-9 |
| `src/chat_compressor/live_models.py` | `extract_model_ids`, `resolve_model_ids`, `grade_arm`; reusable ingestion and grading |
| `src/chat_compressor/translate/vocab_bridge.py` | Discrete-text guarantee that makes hopping possible |
| `src/chat_compressor/metrics.py` | `estimate_tokens`; site for CC-6 |
| `schema/ctx-graph.v1.json` | Schema not to widen; bitemporal fields to mirror |
| `docs/HOOK_CONTRACT.md` | Hook return shapes and managed env keys; update for CC-9 |
| `engine/env.example` | New environment knobs documented here |
