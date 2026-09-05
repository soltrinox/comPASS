# M3 Advisor evidence

- Advisory writer emits `compass-advisory/v1` JSON + markdown companion.
- Freshness: `expires_at` future + required fields.
- Fail-open: missing/stale/malformed ignored by consumers; writer `strict=False` returns None.
- Suite: 74 pytest tests (6 advisory).
