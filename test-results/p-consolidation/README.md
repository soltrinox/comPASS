# Stage P — consolidation evidence

**Date:** 2026-09-07 (PT) / 2026-09-08T03:32Z
**Branch:** `feat/consolidation-and-wasmer` (stacked on `feat/docker-browser-challenge`)
**Scope:** Part A of the consolidation plan — todos `a1-framework`, `a2-demote`, `a3-schema`.
**Not in scope here:** Part B (Wasmer publish / browser SDK / desktop / mobile) and the
cross-cutting proof report. This directory records **this stage only**.

## Artifacts

| File | What it captures |
|---|---|
| `consolidation-validation-<ts>.log.txt` | Full stage run: schema tests, unit suite, `sync_schema --check`, digests, banner check, ground-truth pointers, link check, sanitization scan |
| `schema-drift-guard-<ts>.log.txt` | **Negative control**: injected byte-level drift, observed the guard fail, repaired with `sync_schema.py`, observed it pass again |
| `evidence.json` | Machine-readable summary of the same claims |

Log files carry the `.log.txt` extension per the SDLC constitution. Note that
`.gitignore` line 15 excludes `test-results/**/*.log.txt` from the repo, so the raw logs
stay local; the claims below reproduce their key lines verbatim so this committed record
stands alone.

## Claims and evidence

| # | Claim | Evidence |
|---|---|---|
| 1 | `docs/FRAMEWORK.md` exists as the canonical framework document, assembled from CHARTER / ARCHITECTURE / STACK / audit, with ADR 0001–0007 stated as current and a supersession ledger in Appendix B | File present; `git show --stat` on the commit; §0 decision table and Appendix B ledger |
| 2 | Every relative link in the touched docs resolves | `[PASS] 179 relative links resolved, 0 broken` |
| 3 | No machine-specific absolute path was introduced | `/Users/ hits=0` for `docs/FRAMEWORK.md`, `scripts/sync_schema.py`, `tests/test_schema.py`, `docs/README.md`, `docs/CHARTER.md`, `docs/ARCHITECTURE.md`, `README.md`. `docs/README.md` previously carried 2 and now carries 0. `docs/STACK.md` retains 1 pre-existing hit inside a *prohibition* sentence, untouched |
| 4 | `PROTOTYPE.md` is demoted, not rewritten | `[PASS] superseded banner present`; `[PASS] points at canonical FRAMEWORK.md`; `git diff --numstat` = `24 1 PROTOTYPE.md`; **1** diff hunk, at line 3; heading count `old=67 new=67` |
| 5 | "Ground truth" now names `docs/FRAMEWORK.md` | `PLANS.md:4`, `docs/README.md:6`, `docs/CHARTER.md:4` all read `**Ground truth:** … FRAMEWORK.md`; `docs/ARCHITECTURE.md:6` adds `**Canonical framework:**`; root `README.md:13` lists it first |
| 6 | The canonical schema stays at `src/compass/schema/model-graph.v1.json` and is the only packaged copy | `dist/compass_router-0.1.0.tar.gz` and `…-py3-none-any.whl` each contain exactly `compass/schema/model-graph.v1.json`; neither contains `schema/` nor `docs/schema/`. Guarded by `test_canonical_schema_is_the_packaged_copy` |
| 7 | All three copies share one digest | `7fe7ea117cf40a692d9d62907a722a529cfcd437ab43873d4d8bf16d86c3bae0` for all three paths (unchanged from the pre-change value — no schema content was modified) |
| 8 | `scripts/sync_schema.py --check` reports sync and exits 0 | `[PASS] all model-graph.v1.json copies share one digest`, `exit=0` |
| 9 | The drift guard actually fails on drift | Negative control: reformatting `docs/schema/model-graph.v1.json` (parses equal, bytes differ) produced digest `4d66f123…`; `sync_schema.py --check` → `check-exit=1`; pytest → `1 failed, 1 passed` where the **failure is `test_schema_mirrors_have_no_checksum_drift`** and the pass is the older semantic-equality test. That asymmetry is the reason the checksum guard was added |
| 10 | The guard is repairable in one command | `python scripts/sync_schema.py` → `[PASS] rewrote docs/schema/model-graph.v1.json (was sha256=4d66f123…)`; re-run → `10 passed` |
| 11 | Target suite green | `python -m pytest tests/test_schema.py` → `10 passed in 0.04s` |
| 12 | No regression introduced in the unit suite | `python -m pytest` → `1 failed, 182 passed`. The single failure is **pre-existing and unrelated** — see below |

## Known pre-existing failure (not caused by this stage)

```
FAILED tests/test_paid_sync.py::test_manual_compass_bundle_api_stays_free
AttributeError: 'str' object has no attribute 'lineage'
  ../comPREssOR/engine/src/chat_compressor/bundle.py:117
```

Reproduced with **this branch's edits stashed**: `1 failed, 4 passed` on
`tests/test_paid_sync.py` alone at the unmodified tree. The fault is in the sibling
comPREssOR engine's `bundle.py`, which this stage does not touch, and which ADR
0002/0003 place outside this repo's edit surface. Graded **NOT_FIXED / out of scope**
rather than papered over.

## Re-run instructions

```bash
cd <repo root>
python -m pytest tests/test_schema.py          # 10 passed
python scripts/sync_schema.py --check          # exit 0, three matching digests
shasum -a 256 src/compass/schema/model-graph.v1.json \
              schema/model-graph.v1.json \
              docs/schema/model-graph.v1.json  # one digest, three paths

# reproduce the negative control
python -c "import json,pathlib; p=pathlib.Path('docs/schema/model-graph.v1.json'); \
p.write_text(json.dumps(json.loads(p.read_text()), indent=4)+chr(10))"
python scripts/sync_schema.py --check          # exit 1, [FAIL] drift
python -m pytest tests/test_schema.py          # test_schema_mirrors_have_no_checksum_drift fails
python scripts/sync_schema.py                  # repair
python -m pytest tests/test_schema.py          # 10 passed
```

## Commit-history note (concurrent branch work)

Four commits were made for this stage. Three are intact:

| Commit | Todo |
|---|---|
| `1e75e66` | `a1-framework` — add `docs/FRAMEWORK.md` |
| `3a95d5c` | `a3-schema` — checksum guard + `scripts/sync_schema.py` |
| `6c4df27` | this evidence directory |

The fourth, `a84612f` (`a2-demote`), was absorbed into `3816465` when a concurrent
agent working the Part B todos on this same branch ran `git commit --amend` while
`a84612f` was `HEAD`. **No content was lost:** all seven files in `3816465` are
byte-identical to `a84612f`, verified with `git diff a84612f HEAD -- <path>` per file.
Only the commit message for that change now reads as the Part B author's. History was
deliberately **not** rewritten to repair the attribution, because the concurrent agent
was still committing and a rebase would have clobbered its work. `a84612f` remains in
the reflog if the mapping ever needs to be shown.

## Grade

| Item | Grade |
|---|---|
| `a1-framework` | **FULL** — document created, links resolve, ADR decisions stated as current |
| `a2-demote` | **FULL** — banner added, body byte-intact, five pointers repointed |
| `a3-schema` | **FULL** — canonical path confirmed by packaging evidence, generator added, checksum guard proven by negative control |
| Unit suite | **PARTIAL** — 182/183; one pre-existing sibling-engine failure, evidenced above |
| Part B (Wasmer) | **NOT_RUN** — owned by a parallel agent; nothing under `wasmer/` or `services/` touched here |
