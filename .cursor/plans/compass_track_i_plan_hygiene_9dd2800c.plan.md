---
name: comPASS Track I — Plan hygiene
overview: Audit Phase 1 Tracks A–E and master plan todos against merged reality; flip completed statuses; fix stale PR-open wording; sync all three plan copies.
todos:
  - id: audit-master-ae
    content: "Audit compass_master_orchestration_b029ab33 + Tracks A–E todos vs git reality (comPREssOR 44460ba, comPASS 16e22ec)"
    status: pending
  - id: flip-completed-todos
    content: "Flip todos that are done in reality to status completed; leave genuinely open items pending with notes"
    status: pending
  - id: fix-stale-pr-wording
    content: "Fix stale 'PR open' / awaiting-merge wording in plan bodies where PRs already merged"
    status: pending
  - id: sync-three-copies
    content: "Byte-sync all Phase 1 plan files across work/.cursor/plans, ~/.cursor/plans, and comPASS/.cursor/plans"
    status: pending
  - id: update-plans-md-phase1-note
    content: "Ensure PLANS.md Phase 1 section notes completion and points at Phase 2 master"
    status: pending
  - id: hygiene-proof
    content: "Record hygiene pass evidence under test-results/i-plan-hygiene/ (diff summary + checksum list)"
    status: pending
isProject: false
---

# comPASS Track I — Plan hygiene

## Purpose

Residual **plan-checkbox hygiene**. Phase 1 code landed; some plan frontmatter still says `pending` or bodies still say “PR open.” Align **A–E + Phase 1 master** with merged reality and keep the **three registered copies** identical.

**Ground truth:** comPREssOR `main` @ `44460ba`; comPASS @ `16e22ec`; existing plans under the three `.cursor/plans/` trees.

**Depends on:** nothing (start immediately). Does not modify product source.

## Locked defaults

- Do not invent new Phase 1 scope.
- Do not mark incomplete work completed.
- Same bytes in all three plan copies after sync.
- No secrets in plan files.

## Deliverable paths

```
/Users/rosario/work/.cursor/plans/compass_*.plan.md          # Phase 1 set synced
/Users/rosario/.cursor/plans/compass_*.plan.md
/Users/rosario/work/comPASS/.cursor/plans/compass_*.plan.md
/Users/rosario/work/comPASS/PLANS.md                        # Phase 1 note + Phase 2 link
/Users/rosario/work/comPASS/test-results/i-plan-hygiene/
```

## Acceptance / test criteria

1. Every Phase 1 todo either `completed` with evidence cite, or still `pending`/`in-progress` with a one-line reality note.
2. No stale “PR open” for merged CC-1..CC-10 / public comPASS.
3. `shasum` (or `sha256`) matches across the three copies for each Phase 1 plan file.
4. Hygiene evidence folder committed or attached in comPASS.

## Dependencies

| Unblocks | Why |
|---|---|
| Honest Phase 2 reporting | Master F–N progress not confused with stale Phase 1 checkboxes |

## Explicit non-goals

- Rewriting Phase 1 plan architecture sections.
- Deleting Phase 1 plans.
- Implementing product features.
