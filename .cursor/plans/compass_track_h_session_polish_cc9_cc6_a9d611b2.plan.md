---
name: comPASS Track H — Session polish (CC-9 / CC-6)
overview: Prove CC-9 advisory handoff and CC-6 cost counters in real Cursor Agent Chat sessions with fail-open session logs under test-results/.
todos:
  - id: session-checklist-doc
    content: "Write manual + scripted checklist for Agent Chat advisory (CC-9) and cost counters (CC-6) under docs/ and scripts/"
    status: completed
  - id: cc9-advisory-path-verify
    content: "Verify advisory appears in Cursor Agent Chat via CC-9 file-based handoff; corrupt advisory never blocks continue"
    status: completed
  - id: cc6-cost-counters-verify
    content: "Verify cost path uses CC-6 counters where registered; document gaps as PARTIAL not silent success"
    status: completed
  - id: fail-open-session-proof
    content: "Capture real session log proving fail-open under advisory corruption / missing router under test-results/h-session-polish/"
    status: completed
  - id: scripted-harness
    content: "Add scripted harness (hook event fixtures) that replays beforeSubmitPrompt/sessionStart shapes without live IDE when possible"
    status: completed
  - id: compressor-docs-only
    content: "Touch comPREssOR docs only if checklist gaps require it — no engine source changes unless explicitly approved later"
    status: completed
  - id: evidence-pack
    content: "Package evidence JSON + .log.txt with FULL/PARTIAL/NOT_RUN grades for CC-9 and CC-6 claims"
    status: completed
isProject: true
---

# comPASS Track H — Session polish (CC-9 / CC-6)

## Purpose

Close the gap between **unit-green** Tier 2 advisor / cost wiring and **real Cursor Agent Chat** behavior. Prove that:

1. Advisory context appears via the **CC-9** handoff path.
2. Cost accounting uses **CC-6** counters where registered.
3. Fail-open holds in a real session (corrupt advisory / missing router never blocks chat).

**Ground truth:** comPREssOR @ `44460ba` CC-6/CC-9; `src/compass/serve/advisory.py`; `test-results/m3-advisor/`; `docs/INTEGRATION.md`.

**Depends on:** Phase 1 B/C complete. Track F optional for live model recommendations. May touch **comPREssOR docs only** if needed — **do not** modify compressor engine source in this track.

## Locked defaults

- Fail-open hook discipline (continue on error).
- Probe/keys never in hook process.
- Advisory is **advisory only** — no model field forcing in hook return shapes.
- Outcome-equivalence language only if any hop recommendation is shown.

## Deliverable paths

```
comPASS/
  docs/session/
    CC9-CC6-CHECKLIST.md              # NEW
  scripts/
    session_polish_harness.py         # NEW
  test-results/h-session-polish/
    session-*.log.txt
    evidence.json
# Optional docs-only on compressor:
comPREssOR/docs/HOOK_CONTRACT.md      # only if checklist requires clarification
```

## Acceptance / test criteria

1. Checklist covers manual IDE steps + scripted harness.
2. At least one real Agent Chat session log shows advisory injection path (or graded NOT_RUN with blocker noted — prefer FULL).
3. Fail-open proof: deliberately corrupt advisory file ⇒ chat continues; log captured.
4. CC-6: counters visible in registered cost path or PARTIAL with explicit missing registration list.
5. No comPREssOR `.py` source diffs from this track.

## Dependencies

| Depends on | Why |
|---|---|
| Phase 1 CC-6/CC-9 | Features exist |
| Track M/F (optional) | Live endpoint names in advisory |
| Unblocks L | Release notes can cite session-proven advisory |

## Explicit non-goals

- Redesigning hook return shapes.
- Engine changes in comPREssOR.
- Claiming identical model outputs across hops in the session UI.
