# q-wasmer-publish — stage evidence (plan B1)

Stage: **B1 registry publish** (`b1-namespace`, `b1-publish`).
Captured 2026-09-07 PT on branch `feat/consolidation-and-wasmer`.

**Outcome: publish is NOT_RUN. Offline packaging is complete and verified.**
Rationale and unblocking steps: [`wasmer/PUBLISH-NOT_RUN.md`](../../wasmer/PUBLISH-NOT_RUN.md).

## Artifacts

| File | Contents |
|---|---|
| `registry-state.txt` | CLI version, auth state, `publish --dry-run` refusal, registry GraphQL namespace/user/package probes plus two control queries |
| `package-build.txt` | `--check` validation with negative controls, local `.webc` build, digest, reproducibility, unpacked contents, `SHA256SUMS` reconciliation, packaged-vs-loose run diff |
| `guards.txt` | `wasmer_size_budget.py`, `wasmer_parity.py`, and four targeted pytest modules after the manifest move |
| `evidence.json` | The same results, machine-readable |
| `compass-decide-0.1.0.webc` | Local package build. **Gitignored** (build output); rebuild to reproduce digest `fe2dfc91…` |

Raw `.log.txt` transcripts are gitignored repo-wide by `.gitignore` line 15, so the
committed evidence uses `.txt` / `.json`, matching the other `test-results/` stages.

## Claim → evidence map

| Claim | Where |
|---|---|
| Wasmer CLI 7.4.0 present | `registry-state.txt` |
| Not authenticated; no token in config or env | `registry-state.txt` |
| `compass` namespace and `compass/decide` package do not exist | `registry-state.txt` (with `wasmer` / `python/python` controls proving the probe works) |
| `wasmer publish --dry-run` cannot run offline — it requires auth first | `registry-state.txt` |
| Root manifest is well-formed | `package-build.txt`, `--check` exit 0 plus two failing negative controls |
| Package identity parses as namespace `compass`, name `decide`, version `0.1.0` | `package-build.txt`, CLI default output filename `compass-decide-0.1.0.webc` |
| `.webc` build is reproducible | `package-build.txt`, two builds → same sha256 |
| Both modules reconcile against `SHA256SUMS` | `package-build.txt`, MATCH lines |
| Packaged run equals loose-artifact run | `package-build.txt`, `diff: IDENTICAL` |
| Existing guards still green | `guards.txt`, all exit 0; 13 tests pass |

## Re-run

```bash
cd <repo root>
wasmer --version && wasmer whoami                 # expect "Not logged in" until unblocked
wasmer package build --check .
wasmer package build -o test-results/q-wasmer-publish/compass-decide-0.1.0.webc .
shasum -a 256 test-results/q-wasmer-publish/compass-decide-0.1.0.webc
# expect fe2dfc91893d692cb350ae92dee38a6c71bd669fd1fd847359f0fab2ffe8b5d9

wasmer run test-results/q-wasmer-publish/compass-decide-0.1.0.webc -- \
  --request "implement a function" \
  --snapshot /wasmer/fixtures/snapshot_min.json \
  --now "2026-09-05T00:00:00Z"

.venv/bin/python scripts/wasmer_size_budget.py
.venv/bin/python scripts/wasmer_parity.py
.venv/bin/python -m pytest tests/test_wasmer_size_budget.py tests/test_wasmer_parity.py \
  tests/test_wasm_boundary.py tests/test_release_metadata.py -q
```

## Not covered here

Cross-cutting proof reporting and the full end-to-end validation suite belong to
the dedicated validation stage, not to B1.
