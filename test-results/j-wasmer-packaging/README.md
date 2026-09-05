# Track J — Wasmer packaging evidence

| Target | Grade | Notes |
|---|---|---|
| Browser headless smoke | FULL | Playwright + Chrome/`chromium`; decide fixture + fail-open |
| Desktop Wasmer shell | FULL | `wasmer/desktop/run-decide.sh` |
| SHA256 / size budget | FULL | `scripts/wasmer_size_budget.py` ≤150000 browser bytes |
| Fail-open parity vs Python | FULL | `scripts/wasmer_parity.py` |
| Mobile device farm | NOT_RUN | `wasmer/mobile/NOT_RUN.md` |

See `evidence.json` for machine-readable grades.
