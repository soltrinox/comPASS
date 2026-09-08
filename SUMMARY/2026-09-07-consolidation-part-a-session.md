# Session summary — consolidation Part A (2026-09-07 PT)

**Branch:** `feat/consolidation-and-wasmer` (stacked on `feat/docker-browser-challenge`)
**Scope:** Part A of the consolidation plan — `a1-framework`, `a2-demote`, `a3-schema`.
**Out of scope:** Part B (`wasmer/`, `services/`) — owned by a concurrent agent this session.
**Evidence:** [`test-results/p-consolidation/`](../test-results/p-consolidation/README.md)

## What changed

| Todo | Result |
|---|---|
| `a1-framework` | [`docs/FRAMEWORK.md`](../docs/FRAMEWORK.md) created — canonical framework document; ADR 0001–0007 stated as current; historical Phase 1–2 layout in Appendix A; supersession ledger in Appendix B |
| `a2-demote` | [`PROTOTYPE.md`](../PROTOTYPE.md) banner-demoted to historical origin brief with its body byte-intact; "Ground truth" repointed in `PLANS.md`, `docs/README.md`, `docs/CHARTER.md`; canonical pointers added to `docs/ARCHITECTURE.md`, `docs/STACK.md`, root `README.md` |
| `a3-schema` | `src/compass/schema/model-graph.v1.json` confirmed canonical and left in place; [`scripts/sync_schema.py`](../scripts/sync_schema.py) generates the two mirrors (`--check` for read-only drift); `tests/test_schema.py` gains a sha256 drift guard and a packaged-path guard |

## Decisions taken

**Canonical schema stays put.** Packaging evidence settled it: `src/compass/schema/model-graph.v1.json`
is the only copy inside the built sdist and wheel (via `[tool.setuptools.package-data]`), and
`loader.py` reads it at runtime. `MANIFEST.in` needed no change and nothing had to move.

**Byte-level guard, not semantic.** The pre-existing test compared parsed JSON, which a reformat
passes while the digests diverge. Proven with a negative control: the reformat failed the new
checksum test while the old semantic test still passed.

**Documentation drift resolved rather than annotated.** Two lines in `docs/CHARTER.md` (the Tier 2
row and non-claim 4) described in-IDE advisory as Tier 2's surface, contradicting ADR 0005 where
they stood. The mechanical fact was kept; the product claim now matches the ADR.

## Left undone, deliberately

- Part B Wasmer work — concurrent owner.
- Cross-cutting proof report and the full e2e validation suite — later dedicated pass.
- `tests/test_paid_sync.py::test_manual_compass_bundle_api_stays_free` fails in the sibling
  comPREssOR engine's `bundle.py:117`. Pre-existing (reproduced with this branch's edits stashed)
  and outside this repo's edit surface per ADR 0002/0003. Graded, not papered over.
- Absolute plan-registry paths elsewhere in `PLANS.md` — pre-existing, out of scope.
