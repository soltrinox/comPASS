---
name: comPASS Track L — PyPI release
overview: Define version scheme, changelog, build/publish dry-run (TestPyPI or documented), GitHub tag, and CI release workflow stub for compass-router.
todos:
  - id: version-scheme
    content: "Document semver scheme for compass-router (0.1.x test-ready → 0.2.0 when gate passes) in docs/RELEASE.md"
    status: pending
  - id: changelog
    content: "Author CHANGELOG.md covering Phase 1 offline stack + Phase 2 test-ready notes placeholders"
    status: pending
  - id: build-sdist-wheel
    content: "Verify python -m build produces sdist+wheel from pyproject; fix packaging metadata gaps"
    status: pending
  - id: testpypi-dry-run
    content: "Dry-run publish via twine --repository-url TestPyPI OR document equivalent gated command; never put tokens in repo"
    status: pending
  - id: github-tag-policy
    content: "Document GitHub tag policy (v0.1.x) and create tag when dry-run succeeds on chosen commit"
    status: pending
  - id: ci-release-stub
    content: "Add CI release workflow stub (manual dispatch) that builds artifacts and optionally publishes with secrets"
    status: pending
  - id: proof-l
    content: "Record release dry-run evidence under test-results/l-pypi-release/"
    status: pending
isProject: true
---

# comPASS Track L — PyPI release

## Purpose

Make **compass-router** releasable: version scheme, changelog, build artifacts, **TestPyPI dry-run** (or documented equivalent), GitHub tagging policy, and a **CI release workflow stub**.

**Ground truth:** `pyproject.toml` name `compass-router` version `0.1.0`; public `soltrinox/comPASS`.

**Depends on:** Tracks H/J preferably stable enough that the package story matches tested surfaces. Does not require Track N.

## Locked defaults

- No secrets in git; use CI secrets / local keyring for twine.
- Fail-open product defaults unchanged by packaging.
- WASM artifacts may be optional extras — document, do not force into pure-Python wheel unless intentional.

## Deliverable paths

```
comPASS/
  docs/RELEASE.md                     # NEW
  CHANGELOG.md                        # NEW
  .github/workflows/release.yml       # NEW stub
  pyproject.toml                      # version bumps as needed
  test-results/l-pypi-release/
```

## Acceptance / test criteria

1. `docs/RELEASE.md` describes version scheme + tag policy.
2. `CHANGELOG.md` exists with Phase 1 section.
3. Local `python -m build` succeeds; twine check clean.
4. TestPyPI dry-run performed **or** documented with exact commands and NOT_RUN grade if credentials absent.
5. CI workflow stub present (manual dispatch); does not publish on every push.

## Dependencies

| Depends on | H/J soft |
| Unblocks | N (versioned dependency story), external install tests |

## Explicit non-goals

- Yanking or breaking existing public git history.
- Publishing secrets.
- Claiming PyPI package = production SLA.
