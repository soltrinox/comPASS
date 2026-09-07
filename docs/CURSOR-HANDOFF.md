# Cursor handoff — comPASS (2026-09-07 PT)

**Purpose:** Close out the Grok Bot (WASMER) session and give Cursor agents a single source of truth for **current status**, **what to open**, and **what to build next**.

**Repo:** [`soltrinox/comPASS`](https://github.com/soltrinox/comPASS)  
**Local tree:** `/Users/rosario/work/comPASS`  
**Compressor sibling:** `soltrinox/comPREssOR` @ `main` (CC-1..CC-10)  
**Open PR:** [#2 Docker browser challenge client](https://github.com/soltrinox/comPASS/pull/2) @ `5082367` (`feat/docker-browser-challenge`)

**Workspace plan (open this in Cursor):**  
[`.cursor/plans/compass_phase3_status_handoff_20260907.plan.md`](../.cursor/plans/compass_phase3_status_handoff_20260907.plan.md)

Also mirrored under `/Users/rosario/work/.cursor/plans/` and `/Users/rosario/.cursor/plans/` when synced.

---

## 1. Product posture (locked)

| Decision | ADR / doc |
|---|---|
| Browser-only Wasmer appliance; no Cursor/IDE product path | [ADR 0005](adr/0005-eni6ma-gated-browser-agent.md), [ARCHITECTURE.md](ARCHITECTURE.md) |
| Generic LLM adapter: decide / catalog / proxy_override | [ADR 0006](adr/0006-generic-llm-adapter.md), [API.md](API.md) §6 |
| Google Antigravity (`agy`) stays **native** behind ENI6MA-gated Express bridge | [ADR 0007](adr/0007-agy-behind-eni6ma-gate.md) |
| Digest is trust root; deny-by-default egress; Probe owns keys | AUDIT + WASMER-DEPLOYMENT |

Pass+ Vercel reference face (not copied wholesale): `https://circuit.eni6ma.com/passplus/?handle=ALICE` / `?binary_url=…`

---

## 2. Phase completion

| Phase | Status |
|---|---|
| **1** Offline A–E (specs, compressor CCs, Graph/Route, Wasmer cut, GTM ADRs) | **Complete** |
| **2** Test-ready F–N | **Complete** (lab/test-ready ≠ production) |
| **3** Browser agent + Gate + adapter + Docker client | **In progress** — scaffold + lab deploy; ceremony product incomplete |

---

## 3. What works today (lab)

### Docker Compose

```bash
docker compose up --build -d
```

| Service | Port | Role |
|---|---|---|
| `agy-bridge` | **8791** | OpenAI-shaped Gate → fake-agy (or live-agy profile) |
| `browser-client` | **8088** | Challenge-first static SPA + `/circuit-proxy` + `/artifacts` |

Smoke:

- http://127.0.0.1:8088/ → redirects to `challenge.html`
- http://127.0.0.1:8088/challenge.html?handle=demo-wasm
- http://127.0.0.1:8791/healthz

Demo circuit pin:

- URL: `https://raw.githubusercontent.com/eni6ma/REGISTRY/feat/wasm-circuits/circuits/demo-wasm/v1/eni6ma_wasm.wasm`
- SHA-256: `853717e421a36fc93d0791d3f2718ecf3e9c449fb3c60d4084dedab3af75c389`
- Local mirror: `wasmer/artifacts/eni6ma/demo-wasm/v1/` + `wasmer/artifacts/pins.json`

### Libraries / paths

| Area | Path | Notes |
|---|---|---|
| Adapter | `src/compass/serve/adapter.py` | Track O done; tests `tests/test_generic_adapter.py` |
| Proxy | `src/compass/serve/proxy.py` | Delegates to adapter |
| Bridge allowlist | `wasmer/browser/bridge.js` | Deny-by-default hosts |
| Circuit load | `wasmer/browser/circuitLoader.js` | SHA-256 fail-closed; `loadPinnedRemote` + proxy |
| Minimal proof | `wasmer/browser/wasmerRunner.js` | DEMO-MINT `build_minimal_proof` |
| Challenge UI | `wasmer/browser/challenge.html` + `challenge.js` | Pass+-style handle / binary_url |
| Stub agent | `wasmer/browser/agent.html` | Older Path-B buttons |
| Gate | `services/agy-bridge/src/circuitGate.js` | Digest + abi_probe; prove-only ABI |
| Docs audit | `docs/AUDIT-GOALS-VS-BROWSER-STACK.md` | Goals → Done/Partial/Not |
| Deploy map | `docs/WASMER-DEPLOYMENT.md` | Zones A–D lifecycle |
| Docker ops | `docs/DOCKER.md` | Compose cheat sheet |

### Readiness (rough)

- Auth→route→LLM **engine** path: ~55–65% testable (compose Gate + adapter + pin)
- Ceremony / verify / burn / full agent boot: ~15–25%
- Grade: **lab/demo**, not production-deploy ready

---

## 4. Not done (Cursor should prioritize)

1. **Merge PR #2** and confirm compose smoke on a clean machine  
2. **Six-color interactive ceremony** (challenge → colors → proof → burn-before-validate) — only Path-B / challenge form exists  
3. **Real verify ABI + burn ledger** — Gate stub / DEMO-MINT prove-only  
4. **Full Wasmer agent boot page** — ceremony → policy bind → triggers → loop → adapter  
5. **Real comPREssOR hop inject** — adapter still has placeholder `default_compress_hook`  
6. Live Probe keys / PyPI TestPyPI / mobile farm — still gated / NOT_RUN as in Phase 2 evidence  
7. Optional: apply leftover `services/agy-bridge-gate-harden.tgz` if still uncommitted on disk  

---

## 5. How Cursor should work this repo

- Prefer **`gh`** on the Mac (`soltrinox` keyring) for branch/PR; box/cloud may lack GitHub auth  
- Cloud Agent may need **GitHub reconnect in Cursor** if launch fails  
- Plans live in **three places** (keep bytes aligned when editing):
  - `/Users/rosario/work/comPASS/.cursor/plans/` (repo)
  - `/Users/rosario/work/.cursor/plans/`
  - `/Users/rosario/.cursor/plans/`
- Index: [`PLANS.md`](../PLANS.md), [`.cursor/plans/README.md`](../.cursor/plans/README.md)
- Refuse edits under archived `CHAT-COMPRESSOR*` (ADR 0002/0003)

---

## 6. Suggested first Cursor prompt

> Open `docs/CURSOR-HANDOFF.md` and `.cursor/plans/compass_phase3_status_handoff_20260907.plan.md`. Merge or finish PR #2, smoke `docker compose` challenge UI on :8088 against agy-bridge :8791, then implement Track P: six-color ENI6MA ceremony UX bound to digest-pinned circuit + burn-before-validate, replacing the minimal-proof stub for product auth.

---

## 7. Session trail (Grok Bot WASMER, Sep 6–7)

- Rewrote architecture for browser-only + ENI6MA; ADRs 0005–0007  
- Implemented Track O generic adapter + tests  
- Built agy-bridge Gate + Compose fake-agy  
- Wrote WASMER-DEPLOYMENT + AUDIT-GOALS-VS-BROWSER-STACK  
- Built Docker `browser-client` challenge UI (PR #2) via `gh` after Cloud Agent GitHub reconnect failed  

**End of Grok Bot handoff.**
