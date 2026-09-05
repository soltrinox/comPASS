# Free-tier scope

**Principle:** the free tier must be genuinely useful and must **never withhold correctness**. Anything required for the router to give *safe* answers stays free. Paid sells marginal cost and network effects.

## **Do not paywall accuracy.**

If free routes *worse* rather than *less conveniently*, trust dies and the free corpus that paid is built from dies with it.

## In the free tier (local, open source, single machine, single user)

- Full Observatory: catalog ingest, price/latency, drift detection, for endpoints the user can already reach
- Local task classification and local capability graph
- Advisory recommendations through the compressor injection surface (CC-9)
- Local routing for **owned** call sites: SDK wrapper and local proxy
- Local probe execution against the user's own corpus, on the user's own keys and budget
- The full portable-state-bundle **format**, plus **manual** export and import — file movement is free
- Single machine, single user, local persistence

## Explicitly not free (automated / fleet / org)

| Paid pillar | What is gated |
|---|---|
| 1 | Automated cross-machine sync |
| 2 | Managed multi-model insertion as a service |
| 3 | Fleet-aggregated managed capability graph |
| 4 | Org-enforced governance |
| 5 | Shared project memory |

## Free-tier sync boundary (Appendix A.5) — closed

**Decision:** Bundle format + manual export/import **stays free**. Only **automated** sync is paid (Pillar 1).

This is a closed product decision for Track E unless product leadership objects in writing. It must not contradict [PAID-PILLARS.md](PAID-PILLARS.md).

## Why free is complete for an individual

Shipping a complete local product is deliberate: it builds the corpus, exposes the reward-signal problem to real usage, and establishes the bundle format as a standard before anyone is asked to pay.
