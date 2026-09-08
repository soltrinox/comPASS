# ADR-quality: Wasmer registry publish — NOT_RUN

**Status:** NOT_RUN (2026-09-07 PT)
**Track:** J / plan B1 (registry publish)
**Manifest:** `wasmer.toml` at repo root (promoted from `wasmer/desktop/wasmer.toml`)
**Package:** `compass/decide` v0.1.0 — modules `compass-decide` (WASI) + `compass-core` (browser cdylib)

## Decision

Do **not** claim a published Wasmer package. Nothing was pushed to `wasmer.io`.
The manifest is promoted, validated, and built to a local `.webc` so the offline
path is complete, but the registry name `compass/decide` does not exist and this
machine cannot create it.

Two independent blockers, both verified:

| Blocker | Evidence | Who can clear it |
|---|---|---|
| No registry credential | `wasmer whoami` → `error: Not logged in registry wasmer.io`; `wasmer config get registry.token` → empty; no `WASMER_TOKEN` in env | Repo owner runs `wasmer login` |
| `compass` namespace unclaimed | `getNamespace(name:"compass")` → `null`, `getUser(username:"compass")` → `null`, `getPackage(name:"compass/decide")` → `null` against `https://registry.wasmer.io/graphql` (control query for `wasmer` returns a real record, so the query itself is sound) | Whoever owns the account, after login |

Publishing under a guessed or squatted namespace was rejected. Creating an
account was out of scope for this agent.

## Context

- Wasmer CLI **7.4.0** is installed at `/opt/homebrew/bin/wasmer`. The tooling is
  not the problem; the credential and the name are.
- `wasmer publish --dry-run .` still refuses without a token — the dry run is
  server-aware, so it is not usable as an offline validator. Use
  `wasmer package build --check .` instead, which does validate (verified against
  a deliberately broken manifest: missing module source and bad `abi` both fail).
- `compass` is **unclaimed**, not taken. Registry search shows only unrelated
  third-party packages with `compass` inside the package name
  (`bagasandika121858f3/clearcompassroom` and similar), all under other users'
  namespaces. No fallback namespace was needed or chosen, because the blocker is
  the missing credential rather than a name collision. Claiming `compass` should
  succeed once someone logs in.
- `publish = false` in `wasmer/crate/Cargo.toml` concerns crates.io and is
  unrelated to this. Left as-is.

## Consequences

- **B3 desktop reconcile is blocked** for its primary goal. `run-decide.sh`
  cannot be rewritten to `wasmer run compass/decide` against the registry. It can
  be rewritten to run the local `.webc` by path, which exercises the packaged
  command and the bundled fixture, with the raw `.wasm` path as the offline
  fallback — but that is packaged-local, not published, and must be graded
  PARTIAL until this file flips.
- **B2 browser SDK is not blocked.** `@wasmer/sdk` work does not require the
  comPASS package to be in the registry; the existing pinned-digest load path
  from `wasmer/artifacts/` stays authoritative.
- Release notes may advertise **locally packaged** wasm. They may not advertise a
  registry package, a `wasmer run compass/decide` install line, or a registry URL.
- No fake green. Faking a publish transcript is forbidden here for the same
  reason it is forbidden in `wasmer/mobile/NOT_RUN.md`.

## What was done instead (offline, complete)

| Step | Result |
|---|---|
| Promote manifest to repo root covering both artifacts | `wasmer.toml`, modules `compass-decide` (`abi = "wasi"`) + `compass-core` (`abi = "none"`) |
| Manifest validation | `wasmer package build --check .` → exit 0 |
| Local package build | `wasmer package build -o …/compass-decide-0.1.0.webc .` → 258019 bytes |
| Package digest | `fe2dfc91893d692cb350ae92dee38a6c71bd669fd1fd847359f0fab2ffe8b5d9` |
| Reproducibility | Repeated builds from an unchanged tree produce a byte-identical `.webc` |
| Digest reconciliation | Both embedded modules match `wasmer/artifacts/SHA256SUMS` exactly (ADR 0005 trust root intact) |
| Packaged execution | `wasmer run <webc> -- --request … --snapshot /wasmer/fixtures/snapshot_min.json` emits a decide envelope byte-identical to the loose-artifact run |

Digests recorded in [`artifacts/PACKAGE-DIGESTS.json`](artifacts/PACKAGE-DIGESTS.json).
Stage evidence in `test-results/q-wasmer-publish/`.

One caveat on that package digest: the `.webc` embeds the contents of
`[package].readme` and `license-file`, so editing `wasmer/README.md` or `LICENSE`
moves it even when no module byte changes. Treat it as a build fingerprint. The
two module digests are the stable trust root and are the ones that must reconcile
against `SHA256SUMS`.

## Pre-publish hygiene finding (fix before the first publish)

Both committed `.wasm` artifacts embed absolute builder paths — 17 occurrences in
`compass-decide.wasm`, 19 in `compass_core_bg.wasm`, all Rust panic-location
strings of the form `/Users/<user>/.asdf/installs/rust/1.89.0/...`. They have been
there since the initial commit and were not introduced by this stage, so nothing
here changed them. Locally they are harmless. Published, they leak the builder's
home directory to anyone who runs `wasmer package unpack`.

The fix is a rebuild with path remapping:

```bash
cd wasmer/crate
RUSTFLAGS="--remap-path-prefix=$HOME=/build --remap-path-prefix=$PWD=/src" \
  cargo build --release --target wasm32-wasip1 --bin compass-decide
# and the same for the wasm32-unknown-unknown --lib target
```

That changes both digests, so it must be its own change: rebuild, refresh
`artifacts/SHA256SUMS`, `artifacts/pins.json`, and
`artifacts/PACKAGE-DIGESTS.json` together, then re-run
`scripts/wasmer_size_budget.py` and `scripts/wasmer_parity.py`. Out of scope for
B1, which is not permitted to move the trust root.

## Exact next steps (when unblocking)

1. **Credential.** On a machine with the owner's Wasmer account:
   ```bash
   wasmer login            # opens browser; writes token to $WASMER_DIR
   wasmer whoami           # must print the account, not "Not logged in"
   ```
   For CI instead, set `WASMER_TOKEN` from a registry API token created at
   `https://wasmer.io/settings/access-tokens`, and pass `--token $WASMER_TOKEN`.
   The token is a secret: it belongs in CI secrets or the shell environment,
   never in this repo.
2. **Namespace.** Claim `compass` under that account (Wasmer creates the
   namespace on first publish into it, or create it explicitly in the web UI).
   Re-verify before publishing:
   ```bash
   curl -s -X POST https://registry.wasmer.io/graphql \
     -H 'Content-Type: application/json' \
     -d '{"query":"{ getNamespace(name: \"compass\") { name } }"}'
   ```
   If `compass` has been taken by someone else in the meantime, pick a fallback
   (`<owner>/compass-decide`), change `[package].name` in the root `wasmer.toml`,
   and update this file — do not publish into a namespace you do not own.
3. **Pre-flight, from the repo root:**
   ```bash
   python scripts/wasmer_size_budget.py         # digests must still match SHA256SUMS
   wasmer package build --check .
   wasmer publish --dry-run .                   # now reaches the server
   ```
4. **Publish and record:**
   ```bash
   wasmer publish . | tee test-results/q-wasmer-publish/publish-$(date -u +%Y%m%d-%H%M%S).log.txt
   wasmer package get compass/decide@0.1.0
   ```
   Copy the registry-reported hash into `wasmer/artifacts/PACKAGE-DIGESTS.json`
   under `published`, and set `publish_state` to `PUBLISHED`. It must reconcile
   against the local `.webc` digest above; if it does not, stop — that is a trust
   root violation, not a formatting difference.
5. **Flip this file** to PUBLISHED with the version, date, and registry URL.
   B3 already wired `wasmer/desktop/run-decide.sh` to try
   `wasmer run compass/decide@0.1.0` when requested, then local `.webc`, then
   the air-gap wasm path. Flipping this file is what turns that first hop from
   a caught NOT_RUN into a live registry run.
6. **Repoint the stale docs** that still describe the manifest as living under
   `wasmer/desktop/`: `docs/WASMER.md` line 63 and `docs/WASMER-DEPLOYMENT.md`
   line 172. Left untouched here because `docs/` was owned by a parallel agent.

## Downstream B3 (2026-09-07)

`wasmer/desktop/run-decide.sh` now implements the three-hop order:

1. Opt-in `wasmer run compass/decide@0.1.0` (`COMPASS_WASMER_USE_REGISTRY=1` / `--registry`)
2. Local `compass-decide-0.1.0.webc` (default; `wasmer package build` if missing)
3. Air-gap `wasmer/artifacts/compass-decide.wasm`

A successful local `.webc` run is **not** a published-package run. Registry-by-name
stays PARTIAL / NOT_RUN until this file flips to PUBLISHED.

## Alternatives considered

| Option | Why deferred |
|---|---|
| Publish under a personal or invented namespace | Squats a name the project does not own; `compass/decide` in every doc would then be wrong |
| Create a Wasmer account from this agent | Out of scope; account ownership is a human decision |
| Ship the `.webc` as a GitHub release asset instead | Reasonable stopgap and does not conflict with publishing later, but it is a distribution decision for the owner, not a substitute for B1 |
| Skip the manifest work until credentials exist | Wastes the sequencing; the manifest, digests, and packaged-run proof are all verifiable offline today |
| Fake a publish transcript | Forbidden — same rule as `mobile/NOT_RUN.md` |
