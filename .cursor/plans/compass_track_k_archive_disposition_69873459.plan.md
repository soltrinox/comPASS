---
name: comPASS Track K — Archive disposition
overview: Decide and execute delete-or-keep for CHAT-COMPRESSOR.archived-0.1.3 with a decision record and README pointer; never restore 0.1.3 identifiers into canonical.
todos:
  - id: inventory-archive-trees
    content: "Inventory /Users/rosario/work/CHAT-COMPRESSOR and CHAT-COMPRESSOR.archived-0.1.3 vs canonical comPREssOR; note unique uncommitted work if any"
    status: pending
  - id: decision-record
    content: "Write decision record (ADR or docs/adr extension) — delete OR keep-with-README-pointer; cite ADR 0002"
    status: pending
  - id: execute-disposition
    content: "Execute delete OR keep; if keep, add README pointer forbidding implementation and linking canonical"
    status: pending
  - id: identifier-scan
    content: "Scan canonical comPREssOR for reintroduced 0.1.3 personal identifiers / absolute /Users/rosario paths in source"
    status: pending
  - id: agent-refuse-note
    content: "Ensure PLANS.md / archive README state agents must refuse edits under archived/0.1.3 trees"
    status: pending
  - id: proof-k
    content: "Record disposition evidence under comPASS/test-results/k-archive/ (no secret leakage)"
    status: pending
isProject: false
---

# comPASS Track K — Archive disposition

## Purpose

Close the filesystem footgun around **`CHAT-COMPRESSOR.archived-0.1.3`** (and any remaining untracked `CHAT-COMPRESSOR` tree). ADR 0002 already forbids implementing against 0.1.3; this track **executes** delete **or** keep-with-pointer.

**Ground truth:** `/Users/rosario/work/CHAT-COMPRESSOR.archived-0.1.3`, `/Users/rosario/work/CHAT-COMPRESSOR`, ADR `docs/adr/0002-working-copy-disposition.md`, canonical `/Users/rosario/work/comPREssOR`.

**Depends on:** Track I soft (docs sync). User confirmation required before irreversible delete.

## Locked defaults

- Never restore 0.1.3 identifiers into canonical.
- Never implement CC-* against archive trees.
- Prefer delete after confirm no unique work; else keep with loud README.

## Deliverable paths

```
/Users/rosario/work/CHAT-COMPRESSOR.archived-0.1.3/README.md   # if keep
/Users/rosario/work/comPASS/docs/adr/0002-working-copy-disposition.md  # amend status
/Users/rosario/work/comPASS/docs/adr/0004-archive-disposition.md       # NEW optional
/Users/rosario/work/comPASS/test-results/k-archive/
```

## Acceptance / test criteria

1. Decision record states DELETE or KEEP with date and rationale.
2. If DELETE: trees gone; if KEEP: README at archive root with canonical pointer + refuse-edit rule.
3. Identifier scan of canonical source is clean (or findings filed, not “fixed” by copying 0.1.3).
4. Evidence folder updated.

## Dependencies

| Parallel with | Track I |
| Unblocks | Cleaner onboarding; reduces wrong-tree edits |

## Explicit non-goals

- Merging 0.1.3 into 0.2.0.
- Modifying comPREssOR engine to “compat” with archive.
- Deleting without inventory when unique work might exist.
