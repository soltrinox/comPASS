# Track K inventory — archive disposition

**Recorded (UTC):** 2026-09-05T20:10:00Z
**Recorded (PT):** 2026-09-05 (Track K session)

## Trees

| Tree | Path | Git | HEAD / version | Approx size (prior ls) |
| --- | --- | --- | --- | --- |
| Archive (0.1.3) | `/Users/rosario/work/CHAT-COMPRESSOR.archived-0.1.3` | no (untracked) | pyproject 0.1.3 | ~236M (incl .venv) |
| Live CHAT-COMPRESSOR | `/Users/rosario/work/CHAT-COMPRESSOR` | yes → soltrinox/comPREssOR | 44460ba | ~3.7M |
| Canonical comPREssOR | `/Users/rosario/work/comPREssOR` | yes → soltrinox/comPREssOR | 44460ba / engine 0.2.0 | ~251M |

## Archive unique / historical value (why KEEP)

- Untracked 0.1.3 lab with whitepapers (`WHITEPAPER-*`), `PROOF.md`, `SYSTEM.md`, `runs/`, `fixtures/`, `test-results/`, `dist/`.
- Contains 0.1.3 identifier / absolute-path divergence vs sanitized 0.2.0 (must **not** be merged forward).
- Local `.env` present in archive (existence only noted; contents **not** copied here).
- Live `CHAT-COMPRESSOR` already re-pointed as fresh clone @ `44460ba` (ADR 0002 acceptance).

## Decision

**KEEP** archive with loud root README. Do not delete `comPREssOR` or live `CHAT-COMPRESSOR`.
