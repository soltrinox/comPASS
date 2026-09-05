# Provider ToS / benchmarking caution checklist

**Track F.** Hard gates live in `compass.probe.tos_policy`. This checklist is the operator-facing companion for live Probe / fleet redistribution.

## Before enabling live Probe

1. Confirm `COMPASS_PROBE_ALLOW_NETWORK` stays **0** unless you intentionally enable egress.
2. Confirm the target host is on the explicit allowlist (see `.env.example` / `network_gate.DEFAULT_ALLOWED_HOSTS`). No wildcards.
3. Load credentials **only** via `compass.probe.credentials` (Track M). Never paste keys into Route, core, hooks, or WASM.
4. Prefer mocked HTTP in CI (`MockHttpTransport`). Do not rely on live smoke for merge gates.

## Comparative language (always)

- Publish **outcome-equivalence** language only — never identical-text claims.
- Do **not** emit a public leaderboard rank from probe data (`public_leaderboard` is forced false on write).
- Cards remain priors; Observations are measured posteriors with `{mean, n, ci95}`.

## Fleet redistribution (Pillar 3)

| Provider | Automated benchmarking | Fleet comparative redistribute |
|---|---|---|
| openai | **deny** | **deny** |
| anthropic | **deny** | **deny** |
| google | review | **deny** (default) |
| huggingface | allow local | allow **anonymized** only |
| openrouter | allow local | allow **anonymized** only (respect upstream) |
| cursor | allow local | **deny** |

Writing an Observation with `fleet_redistribute=True` for a denylisted provider raises `TosViolation` (hard gate, not a warning).

## Operator sign-off (optional live smoke)

- [ ] I read the provider terms for every endpoint I will call.
- [ ] I will not redistribute forbidden comparative outputs to the fleet.
- [ ] Keys are in env/keychain only; nothing committed.
- [ ] Route remains fail-open if Probe is down or network is denied.

See also: [LIVE-SMOKE.md](LIVE-SMOKE.md), [CREDENTIALS.md](CREDENTIALS.md), [../gtm/PAID-PILLARS.md](../gtm/PAID-PILLARS.md) Pillar 3.
