# Positioning — comPASS vs aggregators and incumbents

**Core distinction (hold in every public sentence):** aggregators answer **"can I reach it"**; comPASS answers **"should I use it, for this, at this budget."**

## Comparison table

| Incumbent | They solve | They do not | comPASS posture |
|---|---|---|---|
| **OpenRouter** (and access aggregators) | Reachability + unified billing across many endpoints | Per-user capability posterior; session memory | **Consume** as catalog source + probe/execution substrate (prototype §11.2). Complementary, not a replacement |
| **Hugging Face Hub** | Cards, weights, community evals | Operational routing against *this user's* task mix | Cards → **priors only**. Never override observations |
| **Cursor bundled auto-select** | Convenient IDE routing | Transparency, portability, user's budget/task mix | Transparent *why*; portable across tools; tuned to measured individual outcomes |
| **LiteLLM / gateways** | Protocol translation, retries, keys | Decision layer | **Reuse** as plumbing. Do not rebuild |
| **Eval vendors / public leaderboards** | Generic offline scores | Online private loop; decision wiring | Online, private, closes the loop. No published aggregate rank from our probes |

## Wedge

**Personal ground truth plus portable memory.** Neither half is separately defensible for long; together they are, because the corpus and the flywheel accrue to whoever holds both.

The compressor is why portable memory exists: the forward payload is discrete text; hop cost is `CHAT_COMPRESSOR_FORWARD_BUDGET`, not transcript length. Tiers 1–3 (Observatory / Advisor / Router) resemble products that already exist; **Tier 4 (Session orchestrator — per-turn routing inside one continuous session) does not.**

## Aggregator dependency posture (Appendix A.3)

**Closed decision for Track E messaging:** OpenRouter (and similar aggregators) are **interchangeable backends**, not a hard sole dependency.

- Preferred: consume at least one aggregator for catalog + probe substrate to collapse integration work.
- Required: ingest and probe paths must tolerate additional/alternate backends (direct provider APIs, other aggregators) so cost model and vendor risk stay controllable.
- Messaging: never "we replace OpenRouter"; always "we decide on top of reachability you already have."

## What we do not claim

- We do not replace Hugging Face Hub or Cursor's product surface.
- We do not publish a public leaderboard rank from managed or local probes.
- We do not claim identical output text across substituted models (see PAID-PILLARS.md Pillar 2).
