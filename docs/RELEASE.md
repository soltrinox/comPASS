# comPASS / compass-router release

**Package:** `compass-router`  
**Repo:** [soltrinox/comPASS](https://github.com/soltrinox/comPASS)  
**Current version:** `0.1.0`  
**License:** Apache-2.0 (`LICENSE`)

This document is the Track L contract: version scheme, changelog policy, tag policy, local build, TestPyPI / PyPI publish, and what is **not** in the wheel.

PyPI publication ≠ production SLA. A versioned wheel does not claim fleet readiness, solved credit assignment, or unrestricted live benchmarking.

## Version scheme

`compass-router` uses **SemVer** (`MAJOR.MINOR.PATCH`) with a `0.x` major while the product is test-ready, not production-declared.

| Band | Meaning | When to bump |
|---|---|---|
| `0.1.x` | Test-ready package story. Phase 1 offline stack + Phase 2 tracks that have exited. | Patch (`0.1.1`, …) for packaging / docs / bugfix that does not change the Route/Graph/Probe contract. |
| `0.2.0` | Phase 2 **test-ready stack exit gate** has passed (F–N evidence under `test-results/`). | Minor: gate in `compass_phase2_test_ready_master_29901715.plan.md`. Still **not** a production SLA. |
| `1.0.0` | Reserved. Do not ship until a later ADR names production readiness. | Major: only after an explicit production-ready ADR. |

Keep these three strings in lockstep on every release:

- `[project].version` in `pyproject.toml`
- `compass.__version__` in `src/compass/__init__.py`
- `compass.core.CORE_MODULE_VERSION` in `src/compass/core/__init__.py` (module surface paired with host ABI + `model-graph/v1`; bump independently **only** if an ADR says the ABI diverged)

Pre-releases, if needed: `0.1.1rc1` (PEP 440). Do not use local version labels (`+githash`) on published artifacts.

## What is in the wheel vs what is not

The published **sdist + wheel are pure-Python**.

| In the wheel | Not in the wheel |
|---|---|
| `compass` package under `src/compass` | `wasmer/artifacts/*.wasm` (see [`WASMER.md`](WASMER.md)) |
| Packaged `compass/schema/*.json` | Browser / desktop / mobile Wasmer shells |
| `compass-proxy` console script | Provider credentials, `.env`, CI secrets |
| Runtime dep: `numpy>=1.26` | Probe live-network (opt-in via env; default OFF) |

Wasmer artifacts are **git-tree siblings**, not a pip extra. Shipping them inside a manylinux wheel would force platform-specific packaging we do not want for `0.1.x`. Install the Python package; clone the repo (or fetch release assets later) if you need WASM bytes.

Optional extras:

- `pip install compass-router[dev]` — pytest, build, twine
- `pip install compass-router[sdk]` — `httpx` for owned call-site wrappers
- `pip install compass-router[hf]` — reserved; currently empty

Fail-open product defaults are **not** changed by packaging.

## Changelog policy

- Every user-visible change lands in [`CHANGELOG.md`](../CHANGELOG.md) under `[Unreleased]`, then moves into the version section at tag time.
- Phase 1 history lives under `[0.1.0]`. Phase 2 remaining work stays under `[Unreleased]` as placeholders until those tracks exit.

## GitHub tag policy

- Tags are **annotated**, named `v<PEP440>` with a leading `v`: `v0.1.0`, `v0.1.1`, `v0.2.0`.
- Tag **the commit on `main`** that contains the version bump + changelog section. Do not tag a dirty tree.
- Message form: `compass-router 0.1.0`.
- **Do not force-push tags.** If a tag is wrong, publish `0.1.1` (or yank on TestPyPI only). Never rewrite a tag that may already be installed.
- Creating `v0.1.0` on `main` after the Track L commit is the first tag.

```bash
git checkout main
git pull --ff-only
# confirm pyproject.toml version == 0.1.0 and CHANGELOG has [0.1.0]
git tag -a v0.1.0 -m "compass-router 0.1.0"
git push origin v0.1.0
```

Pushing `v*` runs `.github/workflows/release.yml` in **build-only** mode (no publish).

## Local build (required)

From the repo root, with the project venv:

```bash
python -m pip install -U pip build twine
python -m build
python -m twine check dist/*
ls -l dist/
```

Expected artifacts for `0.1.0`:

- `dist/compass_router-0.1.0.tar.gz` (sdist)
- `dist/compass_router-0.1.0-py3-none-any.whl` (purelib wheel)

`dist/` is gitignored. Record checksums under `test-results/l-pypi-release/` when proving a cut.

Verify the wheel is pure-Python and includes schema JSON:

```bash
python -m pip install dist/compass_router-0.1.0-py3-none-any.whl
python -c "import compass, importlib.resources as r; print(compass.__version__); print(r.files('compass.schema'))"
```

## TestPyPI dry-run (gated)

**Never** put tokens in the repo, in `CHANGELOG.md`, or in evidence files. Use a local env var or CI secret.

Credentials looked for (any one is enough for a local upload):

- `TWINE_PASSWORD` + optional `TWINE_USERNAME` (default `__token__`)
- `TWINE_TEST_TOKEN` / `TEST_PYPI_API_TOKEN` / `TESTPYPI_API_TOKEN`

If **none** of those are set, grade the upload **NOT_RUN** and stop after `twine check`.

Exact commands when a TestPyPI API token **is** available:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD='pypi-...'   # TestPyPI token; not a production PyPI token
python -m twine upload --repository testpypi dist/*
# or equivalently:
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

Install from TestPyPI (isolated venv; numpy may need `--extra-index-url` pypi.org):

```bash
python -m pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  compass-router==0.1.0
```

## Production PyPI (do not run casually)

Production publish requires an explicit operator decision **and** a production token (`TWINE_PASSWORD` against pypi.org, or `PYPI_API_TOKEN`). Track L does **not** authorize an unattended production upload.

```bash
# ONLY with a production token you intend to use, after TestPyPI looks right:
export TWINE_USERNAME=__token__
export TWINE_PASSWORD='pypi-...'   # production token
python -m twine upload dist/*
```

CI equivalent: GitHub Actions `workflow_dispatch` with `publish_target=pypi` **and** repository secret `PYPI_API_TOKEN`. Tag-push alone never publishes.

## CI release workflow stub

[`.github/workflows/release.yml`](../.github/workflows/release.yml):

| Trigger | Build + `twine check` | Publish |
|---|---|---|
| `push` of tag `v*` | yes | **no** |
| `workflow_dispatch` `publish_target=none` (default) | yes | **no** |
| `workflow_dispatch` `publish_target=testpypi` | yes | TestPyPI, only if `TESTPYPI_API_TOKEN` secret is set |
| `workflow_dispatch` `publish_target=pypi` | yes | PyPI, only if `PYPI_API_TOKEN` secret is set |
| push / PR to `main` | **no** (this workflow does not run) | **no** |

Regular CI remains [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) and does not publish.

Required GitHub secrets (create in the repo settings; never commit):

- `TESTPYPI_API_TOKEN` — TestPyPI API token (`pypi-...`)
- `PYPI_API_TOKEN` — production PyPI API token (optional; omit until an operator decides)

## Evidence

Track L proofs live under [`test-results/l-pypi-release/`](../test-results/l-pypi-release/). Grades: `FULL` / `PARTIAL` / `NOT_RUN`.

## Non-goals

- Yanking or rewriting public git history.
- Publishing secrets or `.env` files.
- Claiming a PyPI package is a production SLA.
- Embedding WASM artifacts in the pure-Python wheel.
