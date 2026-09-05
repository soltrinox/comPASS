# ADR 0002 — Working-copy disposition (CHAT-COMPRESSOR)

**Status:** Accepted — re-point to canonical checkout  
**Date:** 2026-09-05 (PT filing)  
**Deciders:** Rosario (repo owner); coordinator may treat **G2 as closed** on the recommended default below  
**Track:** E (Product & GTM)  
**Closes:** Prototype Appendix A.2 / §17.1; master todo `decision-working-copy`  
**Gate:** G2 — disposition decided; Track B must refuse edits to CHAT-COMPRESSOR regardless

---

## Context

Verified facts (prototype §17.1):

| Tree | Path | Git | Engine |
|---|---|---|---|
| **Canonical** | `/Users/rosario/work/comPREssOR` | `git@github.com:soltrinox/comPREssOR.git`, branch `main`, clean | **0.2.0** |
| **Working copy** | `/Users/rosario/work/CHAT-COMPRESSOR` | **Not a git repository** (`git rev-parse` fails) | **0.1.3** |
| Related distro | `soltrinox/OPENCLAW-comPREssOR` | separate | do not confuse |

Three-file divergence: `hook_cli.py` differs mainly by version stamp; `graph.py` and `live_models.py` differ because canonical **removed hardcoded personal identifiers**:

- working copy: `FORBIDDEN_WORKSPACE = Path("/Users/rosario/work")`
- canonical: generic project-root guard; identifier regex drops `rosario`

Canonical 0.2.0 is a **sanitized public-release line**, not a stale fork. Implementing CC-* against the untracked 0.1.3 tree and porting later would reintroduce exactly the identifiers stripped for publication.

## Options

1. **Delete** `/Users/rosario/work/CHAT-COMPRESSOR` after Rosario confirms there is no unique uncommitted work worth keeping.
2. **Re-point** it as a fresh checkout of the canonical remote (replace contents; do **not** merge 0.1.3 identifiers forward).

**Forbidden:** implement CC-* against the untracked 0.1.3 tree and port later.

## Recommendation (G2 default)

**Stop using `CHAT-COMPRESSOR` as an implementation target immediately.** Treat the folder as **archival** until Rosario chooses delete (option 1) or re-point (option 2).

Operational rules in force now (no folder deletion performed by this track):

1. Canonical implementation target is **only** `/Users/rosario/work/comPREssOR` (engine 0.2.0, `main`).
2. Track B (and any other agent) **must refuse** to edit `/Users/rosario/work/CHAT-COMPRESSOR`.
3. Do **not** merge 0.1.3 personal-identifier / absolute-path divergence forward into canonical.
4. Physical delete or re-point is deferred to Rosario confirmation; Track E does not delete the folder.

Coordinator **may mark G2 closed**: the disposition decision is recorded with a clear recommended default. Remaining user action is only the irreversible filesystem step (delete vs replace-with-checkout), not "which tree is canonical."

## Decision (recorded)

| Field | Value |
|---|---|
| Implementation target | `/Users/rosario/work/comPREssOR` @ 0.2.0 `main` only |
| CHAT-COMPRESSOR role | Archival / non-target until user confirms delete or re-point |
| Merge 0.1.3 → 0.2.0 | **No** |
| Agent edit policy | Refuse all CC-* and other edits under CHAT-COMPRESSOR |
| Physical cleanup | Awaiting Rosario: prefer **delete after confirm no unique work**, else re-point as clean checkout |

## Consequences

- M0 / Track B start is unblocked on tree selection.
- Leaving the untracked near-duplicate in the workspace remains a footgun; delete or re-point should follow soon after confirm.
- OPENCLAW-comPREssOR remains a separate distribution and is out of scope for this ADR.

## Confirmation checklist (for Rosario)

- [ ] Confirm no unique uncommitted work in CHAT-COMPRESSOR worth preserving
- [ ] Choose **delete** (preferred after confirm) or **re-point** as clean checkout of soltrinox/comPREssOR
- [ ] Optionally flip status to `Accepted` after the filesystem action is done


## Acceptance

Accepted by Rosario via chat 2026-09-05 (PT): **re-point** `/Users/rosario/work/CHAT-COMPRESSOR` as a fresh checkout of `soltrinox/comPREssOR` (do not merge 0.1.3 identifiers). Prior tree archived aside if needed.
