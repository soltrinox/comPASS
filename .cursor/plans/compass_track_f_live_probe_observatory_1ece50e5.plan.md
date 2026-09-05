---
name: comPASS Track F — Live Probe/Observatory
overview: Enable env-gated live Probe/Observatory HTTP transports (HF/OpenRouter/Cursor) with terms-safe allowlists, rate limits, Observation persistence, and never-block-Route isolation.
todos:
  - id: network-gate-allowlist
    content: "Wire COMPASS_PROBE_ALLOW_NETWORK behind explicit host allowlist; default deny; document in .env.example and docs/INTEGRATION.md"
    status: pending
  - id: http-transport-hf-openrouter
    content: "Implement HTTP transports for Hugging Face + OpenRouter catalog ingest and canary probe calls (native Probe only)"
    status: pending
  - id: http-transport-cursor-catalog
    content: "Implement Cursor catalog/canary transport using Probe-only credentials; never import into Route/WASM"
    status: pending
  - id: tos-benchmark-denylist
    content: "Encode provider ToS / automated-benchmarking denylist; block fleet redistribution of forbidden comparative outputs"
    status: pending
  - id: rate-limits-backoff
    content: "Add per-provider rate limits, jittered backoff, and budget caps for live probe fan-out"
    status: pending
  - id: observation-persistence
    content: "Persist Observation nodes into Graph store with {mean,n,ci95} and bitemporal supersede on fingerprint change"
    status: pending
  - id: route-isolation-proof
    content: "Prove Route/decide path never awaits Probe HTTP; fail-open when network denied or Probe down"
    status: pending
  - id: mocked-http-tests
    content: "Add mocked HTTP unit/integration tests for transports, denylist, and rate-limit behavior"
    status: pending
  - id: live-smoke-doc
    content: "Optional env-gated live smoke + committed dry-run live smoke doc and terms checklist under docs/ and test-results/"
    status: pending
isProject: true
---

# comPASS Track F — Live Probe/Observatory

## Purpose

Turn the **offline** Observatory/Probe fixtures into **terms-safe, env-gated live transports** for Hugging Face, OpenRouter, and Cursor catalog + canary probing — without ever putting Probe on the prompt path or letting network failure block Route.

**Ground truth:** Phase 1 offline Tier 1–2 (`src/compass/ingest/`, `src/compass/probe/`), `.env.example` (`COMPASS_PROBE_ALLOW_NETWORK=0`), `docs/gtm/PAID-PILLARS.md` Pillar 3 constraints, prototype §12 probing.

**Depends on:** Track M (credentials) before any non-mocked live smoke. Track I optional (hygiene). Does not modify comPREssOR source.

## Locked defaults

- Fail-open Route; Probe never on prompt path.
- No keys in WASM / `compass.core` / hook process.
- Live network **off** until `COMPASS_PROBE_ALLOW_NETWORK` is truthy **and** target host is on allowlist.
- Outcome-equivalence only in any published comparative language — no identical-text claims; no public leaderboard rank from probe data.
- Provider ToS / benchmarking restrictions are **hard gates**, not warnings.

## Deliverable paths

```
comPASS/
  .env.example                          # document gates + allowlist knobs
  src/compass/probe/
    runner.py                           # live call path (native)
    canary.py
    network_gate.py                     # NEW — allowlist + COMPASS_PROBE_ALLOW_NETWORK
    rate_limit.py                       # NEW
    tos_policy.py                       # NEW — denylist
  src/compass/ingest/
    huggingface.py / openrouter.py / cursor.py   # live HTTP behind gate
  docs/
    INTEGRATION.md                      # live probe section
    probe/
      TERMS-CHECKLIST.md                # NEW
      LIVE-SMOKE.md                     # NEW dry-run + gated smoke
  tests/
    test_probe_network_gate.py          # NEW
    test_probe_live_transports_mocked.py # NEW
  test-results/f-live-probe/            # proofs
```

## Acceptance / test criteria (“test-ready” for F)

1. With `COMPASS_PROBE_ALLOW_NETWORK=0`, all live call sites raise a typed deny / return fixture path; Route unit tests still green.
2. Mocked HTTP suite covers HF, OpenRouter, Cursor catalog + canary success/4xx/timeout.
3. Denylist prevents writing forbidden comparative Observation payloads marked for fleet redistribute.
4. Rate limiter caps concurrent outbound calls; proof log under `test-results/f-live-probe/`.
5. Observations persist and supersede on fingerprint change.
6. Import audit: `compass.route`, `compass.core`, wasmer crate do not reference `network_gate` secret or HTTP clients.
7. Exit artifacts: `docs/probe/TERMS-CHECKLIST.md` + `docs/probe/LIVE-SMOKE.md` committed; optional live smoke graded PARTIAL/FULL only when env present.

## Dependencies

| Depends on | Why |
|---|---|
| Track M | Real credentials for optional live smoke |
| Track I (soft) | Honest Phase 1 checkbox state |
| Unblocks G, H (live), N (fleet) | Schema hooks + live Observation stream |

## Explicit non-goals

- Exhaustive probing of every endpoint (bandit-pruned only).
- Public leaderboard or unrestricted comparative publication.
- Putting fetch inside WASM browser module.
- Modifying comPREssOR.
- Claiming production fleet readiness.

## Implementation notes

1. Prefer injecting an `HttpTransport` protocol so tests never need real sockets.
2. Allowlist hosts explicitly (e.g. `huggingface.co`, `openrouter.ai`, Cursor API host) — no wildcard `*`.
3. Canary sets stay corpus-derived from user history fixtures by default; live expansion is opt-in.
4. When denied, Observatory continues serving last-known catalog snapshot (fail-open for Route consumers).
