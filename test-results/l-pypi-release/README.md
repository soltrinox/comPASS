# Track L — PyPI / release evidence

Date: 2026-09-05 (PT)

| Target | Grade | Notes |
|---|---|---|
| Version scheme `0.1.0` | FULL | `pyproject.toml` + `compass.__version__` + `CORE_MODULE_VERSION` |
| CHANGELOG + `docs/RELEASE.md` | FULL | Phase 1 section + tag / TestPyPI policy |
| `python -m build` sdist+wheel | FULL | `dist/compass_router-0.1.0-py3-none-any.whl`, `dist/compass_router-0.1.0.tar.gz` |
| `twine check` | FULL | both artifacts PASSED |
| Wheel purity | FULL | schema JSON present; no `.wasm` in wheel |
| TestPyPI upload | NOT_RUN | no twine / TestPyPI token in env; commands in `NOT_RUN-testpypi.txt` |
| Production PyPI | NOT_RUN | plan forbids unattended production publish |
| CI release stub | FULL | `.github/workflows/release.yml` manual dispatch; tag-push builds only |
| Pytest | FULL | 147 passed (`--ignore=tests/test_wasmer_parity.py`) |

Publish grade for this cut: **NOT_RUN**.

See `evidence.json`.
