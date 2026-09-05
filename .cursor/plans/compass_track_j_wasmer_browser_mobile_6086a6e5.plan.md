---
name: comPASS Track J — Wasmer browser/mobile
overview: Advance beyond current wasm artifacts with headless browser smoke, CI job, and mobile packaging (or documented Wasmer desktop shell); keep fail-open parity vs Python.
todos:
  - id: headless-browser-smoke
    content: "Headless browser smoke for wasmer/browser sandbox loading compass_core_bg.wasm and exercising decide()"
    status: pending
  - id: ci-browser-job
    content: "Add CI job for headless browser Wasmer smoke (no provider keys); artifact upload of log"
    status: pending
  - id: mobile-or-desktop-shell
    content: "Lift mobile NOT_RUN → at least one iOS/Android host OR documented Wasmer desktop shell packaging beyond raw wasm bytes"
    status: pending
  - id: packaging-runbook
    content: "Update docs/WASMER.md with browser CI, mobile/desktop packaging steps, and graded matrix"
    status: pending
  - id: fail-open-parity-reaffirm
    content: "Re-run scripts/wasmer_parity.py; ensure browser path matches Python defaults on corrupt/missing snapshot"
    status: pending
  - id: size-budget-guard
    content: "CI guard on wasmer/artifacts SHA256SUMS + size budget regression for browser cdylib"
    status: pending
  - id: proof-j
    content: "Emit test-results/j-wasmer-packaging/ with FULL/PARTIAL/NOT_RUN per target"
    status: pending
isProject: true
---

# comPASS Track J — Wasmer browser/mobile

## Purpose

Phase 1 built **Wasmer artifacts** and a browser sandbox page; **mobile device matrix remains NOT_RUN**. This track adds **headless browser smoke + CI**, and moves packaging to **at least one** mobile (iOS/Android) **or** a documented **Wasmer desktop shell** — still Route+Graph read only, Probe native.

**Ground truth:** `wasmer/artifacts/`, `wasmer/browser/`, `docs/WASMER.md`, `scripts/wasmer_parity.py`, `test-results/wasmer-parity/`.

**Depends on:** Phase 1 Track D artifacts. Independent of live F except optional live canary (out of scope here).

## Locked defaults

- No keys / no fetch in browser module.
- Fail-open parity vs Python `compass.core`.
- Probe remains native sidecar.
- Outcome-equivalence non-claim unchanged.

## Deliverable paths

```
comPASS/
  wasmer/browser/                     # smoke hooks
  wasmer/desktop/                     # NEW optional shell packaging
  wasmer/mobile/                      # NEW or docs-only stub
  .github/workflows/wasmer-browser.yml # NEW
  docs/WASMER.md                      # update matrix
  scripts/wasmer_browser_smoke.*      # NEW
  test-results/j-wasmer-packaging/
```

## Acceptance / test criteria

1. Headless smoke loads sandbox and returns a RouteDecision JSON for fixture snapshot.
2. CI job green on PR without secrets.
3. Mobile **or** desktop shell: packaged entrypoint documented; graded FULL or PARTIAL with rationale.
4. Parity script still green; size budget not regressing beyond documented threshold.
5. Import/boundary test still asserts empty fetch import table on browser build.

## Dependencies

| Soft-depends | Why |
|---|---|
| Track F | Only if wanting live browser canary (not required) |
| Unblocks L | Release can advertise browser-tested wasm |

## Explicit non-goals

- Moving Probe into WASM.
- App Store submission.
- Replacing Python native path.
