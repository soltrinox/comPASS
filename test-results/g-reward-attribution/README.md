# Track G — Hop reward attribution proof

## Re-run

```bash
cd /Users/rosario/work/comPASS
.venv/bin/python -m pytest tests/test_reward_attribution.py -q
.venv/bin/python -m pytest -q
```

## Artifacts

| File | Meaning |
|---|---|
| `pytest-attribution.txt` | Focused attribution suite |
| `pytest-full.txt` | Full suite green evidence |
| `schema-link.json` | Points at design doc + ADR + join fields |

## Explicit non-claims

- Credit assignment across hops is **NOT solved**.
- Trajectory / episode policies are **recording conventions** for later re-scoring.
- `counterfactual_later` is a **stub** only.
- Optional bandit update (feature-flagged) does **not** claim optimality.
