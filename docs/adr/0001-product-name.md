# ADR 0001 — Product name

**Status:** Accepted  
**Date:** 2026-09-05 (PT filing)  
**Deciders:** Rosario (product owner)  
**Track:** E (Product & GTM)  
**Closes:** Prototype Appendix A.1; master todo `decision-name` (filed, not irrevocably locked)  
**Gate:** G3 — Accepted 2026-09-05; public remote may be created as `comPASS` / package `compass-router`

---

## Context

`comPASS` is a placeholder chosen to match the `comPREssOR` house style. The GitHub remote name, PyPI package name, WASM artifact prefix, and marketing header are awkward to change after first public publication. Track C scaffolding and Track D deploy artifacts will follow whatever name is recorded here.

Until this ADR is `Accepted`, all tracks continue using `comPASS` and package name `compass-router` (locked default in the master plan).

## Options

| # | Product name | Package / artifact | Notes |
|---|---|---|---|
| 1 | **comPASS** (keep) | `compass-router` | House-style sibling to comPREssOR; already used across plans, PROTOTYPE.md, and docs |
| 2 | MODEL-GRAPH | `model-graph` (TBD) | Descriptive of the capability-graph core; less distinctive as a product brand |
| 3 | ROUTE-GRAPH | `route-graph` (TBD) | Emphasizes the Route plane; underweights Observatory / Advisor / portable memory |
| 4 | ENI6MA-namespaced | portfolio-dependent | Only if this project sits inside the ENI6MA portfolio; also triggers Appendix A.6 registry entry under `ENI6MA-REGISTRY/projects/` |

## Recommendation (default until confirmed)

**Keep `comPASS` as the working product name** and **`compass-router` as the Python package name** until brand is deliberately locked.

Rationale:

- Consistency with existing prototype, plans, and sibling `comPREssOR` naming.
- Avoids a mid-scaffold rename tax on Track C / D before public remote exists.
- Leaves room to accept option 2–4 later without implying the current tree is wrong — only that brand lock is deferred.
- ENI6MA namespacing (option 4) remains open pending Appendix A.6; do not invent a rename in CI.

## Decision (proposed)

| Field | Value |
|---|---|
| Product working name | `comPASS` |
| Package name | `compass-router` |
| PyPI / artifact prefix | follow package name |
| Public remote | **do not create** until this ADR is `Accepted` |
| ENI6MA registry | deferred; note in CHARTER if Track A already filed one |

**Status remains Proposed until Rosario explicitly accepts, rejects, or substitutes an option.** Coordinator may treat G3 as "ADR filed," not "name irrevocably locked."

## Consequences

- GitHub repo name, PyPI name, WASM artifact prefix, and GTM one-pager header all follow the accepted name.
- Track C must not invent a rename in CI or scaffolding beyond `compass-router` / `comPASS`.
- If option 4 is later chosen, open Appendix A.6 and update CHARTER accordingly.

## Confirmation checklist (for Rosario)

- [ ] Accept keep-`comPASS` / `compass-router`, or
- [ ] Choose MODEL-GRAPH / ROUTE-GRAPH / ENI6MA-namespaced and state the exact strings
- [ ] If ENI6MA: confirm registry path and portfolio branding
- [ ] Flip this ADR status to `Accepted` with date before creating any public remote


## Acceptance

Accepted by Rosario via chat confirmation 2026-09-05 (PT): keep product name **comPASS**, package **compass-router**. Public remote authorized.
