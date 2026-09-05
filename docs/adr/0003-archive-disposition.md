# ADR 0003 — Archive disposition (CHAT-COMPRESSOR.archived-0.1.3)

**Status:** Accepted — KEEP with loud README  
**Date:** 2026-09-05 (PT filing)  
**Deciders:** Rosario (repo owner); Track K (W-K) executed  
**Track:** K (Archive disposition)  
**Closes:** Phase 2 Track K; extends ADR 0002 physical-cleanup step for the archived 0.1.3 tree  
**Cites:** ADR 0002 — Working-copy disposition

---

## Context

ADR 0002 recorded that `/Users/rosario/work/CHAT-COMPRESSOR` was an untracked **0.1.3** lab and must not be an implementation target. Acceptance re-pointed that path as a fresh checkout of `soltrinox/comPREssOR` @ `44460ba`.

The prior 0.1.3 contents remain at:

`/Users/rosario/work/CHAT-COMPRESSOR.archived-0.1.3`

That archive is untracked, contains historical whitepapers / PROOF / runs / fixtures, hardcodes absolute `/Users/rosario/...` paths and `FORBIDDEN_WORKSPACE`, and may hold a local `.env`. Leaving it unlabeled is a filesystem footgun for agents.

Canonical implementation target remains **only** `/Users/rosario/work/comPREssOR` (engine **0.2.0**).

## Options

1. **DELETE** the archived tree after confirming no unique historical value.
2. **KEEP** the archived tree with a loud root README forbidding use / implement / merge of identifiers.

## Decision

| Field | Value |
| --- | --- |
| Disposition | **KEEP** |
| Archive path | `/Users/rosario/work/CHAT-COMPRESSOR.archived-0.1.3` |
| Archive README | Present — do-not-use / refuse-edit / do-not-merge-identifiers |
| Legacy README | Preserved as `README.legacy-0.1.3.md` |
| Live `CHAT-COMPRESSOR` | Fresh clone @ `44460ba` — **do not delete** |
| Canonical `comPREssOR` | Engine 0.2.0 — **do not delete** |
| Merge 0.1.3 → 0.2.0 | **No** |
| Agent edit policy | Refuse all edits under archived / 0.1.3 trees |

### Rationale

- Archive retains unique historical artifacts not in the sanitized 0.2.0 public tree.
- Safer default vs irreversible delete when unique value is present.
- ADR 0002 re-point already closed the live working-copy path; Track K only labels the aside archive.
- Identifier scan of canonical `engine/`, `extension/`, `scripts/`, `docs/` is **clean** (no reintroduced 0.1.3 personal identifiers).

## Consequences

- Onboarding footgun reduced by README + PLANS.md refuse note.
- Agents must refuse CC-* / comPASS implementation against the archive.
- Physical delete remains available later if Rosario chooses; not required for Track K acceptance.
- Evidence: `comPASS/test-results/k-archive/`.

## Acceptance

Accepted 2026-09-05 (PT) by Track K execution under Phase 2 defaults (prefer KEEP with README).
