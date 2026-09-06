# comPASS program plans

**Date:** 2026-09-05  
**Ground truth:** [`/Users/rosario/work/comPASS/PROTOTYPE.md`](/Users/rosario/work/comPASS/PROTOTYPE.md)  
**Summary:** [`/Users/rosario/work/comPASS/SUMMARY/2026-09-03-comPASS-prototype-session.md`](/Users/rosario/work/comPASS/SUMMARY/2026-09-03-comPASS-prototype-session.md)  
**Canonical compressor:** `git@github.com:soltrinox/comPREssOR.git` at [`/Users/rosario/work/comPREssOR`](/Users/rosario/work/comPREssOR) (engine 0.2.0, `main` @ `44460ba`, CC-1..CC-10)  
**Public sibling:** [`https://github.com/soltrinox/comPASS`](https://github.com/soltrinox/comPASS) @ `16e22ec`

Each plan is registered in three places (identical bytes). Prefer the work copy when opening from this tree.

## Phase 1 — Offline stack (A–E) — complete

Offline Tier 1–4 + Wasmer artifacts with Python fail-open parity. Phase 2 Track I plan-checkbox hygiene completed 2026-09-05 (PT): A–E + Phase 1 master todos aligned with merged reality (comPREssOR `main` @ `44460ba` PRs #1–#4; comPASS public with Tier 1–4 + Wasmer; ADRs 0001/0002 Accepted). Further program work continues under the Phase 2 master below.

| Track | Name | Cursor plan (work) | User plans | Repo copy |
| --- | --- | --- | --- | --- |
| Master | comPASS Master Orchestration | [`/Users/rosario/work/.cursor/plans/compass_master_orchestration_b029ab33.plan.md`](/Users/rosario/work/.cursor/plans/compass_master_orchestration_b029ab33.plan.md) | [`/Users/rosario/.cursor/plans/compass_master_orchestration_b029ab33.plan.md`](/Users/rosario/.cursor/plans/compass_master_orchestration_b029ab33.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_master_orchestration_b029ab33.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_master_orchestration_b029ab33.plan.md) |
| A | comPASS Track A — Specs & Docs | [`/Users/rosario/work/.cursor/plans/compass_track_a_specs_docs_31e0c88a.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_a_specs_docs_31e0c88a.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_a_specs_docs_31e0c88a.plan.md`](/Users/rosario/.cursor/plans/compass_track_a_specs_docs_31e0c88a.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_a_specs_docs_31e0c88a.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_a_specs_docs_31e0c88a.plan.md) |
| B | comPASS Track B — Compressor Prerequisites | [`/Users/rosario/work/.cursor/plans/compass_track_b_compressor_prereqs_2f4c3239.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_b_compressor_prereqs_2f4c3239.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_b_compressor_prereqs_2f4c3239.plan.md`](/Users/rosario/.cursor/plans/compass_track_b_compressor_prereqs_2f4c3239.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_b_compressor_prereqs_2f4c3239.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_b_compressor_prereqs_2f4c3239.plan.md) |
| C | comPASS Track C — Sibling Engine | [`/Users/rosario/work/.cursor/plans/compass_track_c_sibling_engine_6b7641d9.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_c_sibling_engine_6b7641d9.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_c_sibling_engine_6b7641d9.plan.md`](/Users/rosario/.cursor/plans/compass_track_c_sibling_engine_6b7641d9.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_c_sibling_engine_6b7641d9.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_c_sibling_engine_6b7641d9.plan.md) |
| D | comPASS Track D — Wasmer Deployment | [`/Users/rosario/work/.cursor/plans/compass_track_d_wasmer_deploy_de4e7aa1.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_d_wasmer_deploy_de4e7aa1.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_d_wasmer_deploy_de4e7aa1.plan.md`](/Users/rosario/.cursor/plans/compass_track_d_wasmer_deploy_de4e7aa1.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_d_wasmer_deploy_de4e7aa1.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_d_wasmer_deploy_de4e7aa1.plan.md) |
| E | comPASS Track E — Product & GTM | [`/Users/rosario/work/.cursor/plans/compass_track_e_product_gtm_30bdaa6f.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_e_product_gtm_30bdaa6f.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_e_product_gtm_30bdaa6f.plan.md`](/Users/rosario/.cursor/plans/compass_track_e_product_gtm_30bdaa6f.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_e_product_gtm_30bdaa6f.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_e_product_gtm_30bdaa6f.plan.md) |

### Phase 1 build order (historical)

Track A → Track B M0/M1 → Track C scaffold/graph/route → Track D Wasmer cut → Track C tiers → Track E (ADRs for name and working-copy should close before public remote / compressor edits).

## Phase 2 — Test-ready stack

Program master: make the offline stack **gated-live / session-proven / releasable** without weakening fail-open or putting keys on Route/WASM.

| Track | Name | Cursor plan (work) | User plans | Repo copy |
| --- | --- | --- | --- | --- |
| P2 Master | Phase 2 — Test-ready stack | [`/Users/rosario/work/.cursor/plans/compass_phase2_test_ready_master_29901715.plan.md`](/Users/rosario/work/.cursor/plans/compass_phase2_test_ready_master_29901715.plan.md) | [`/Users/rosario/.cursor/plans/compass_phase2_test_ready_master_29901715.plan.md`](/Users/rosario/.cursor/plans/compass_phase2_test_ready_master_29901715.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_phase2_test_ready_master_29901715.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_phase2_test_ready_master_29901715.plan.md) |
| F | Live Probe/Observatory | [`/Users/rosario/work/.cursor/plans/compass_track_f_live_probe_observatory_1ece50e5.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_f_live_probe_observatory_1ece50e5.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_f_live_probe_observatory_1ece50e5.plan.md`](/Users/rosario/.cursor/plans/compass_track_f_live_probe_observatory_1ece50e5.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_f_live_probe_observatory_1ece50e5.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_f_live_probe_observatory_1ece50e5.plan.md) |
| G | Hop reward attribution | [`/Users/rosario/work/.cursor/plans/compass_track_g_hop_reward_attribution_10a51057.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_g_hop_reward_attribution_10a51057.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_g_hop_reward_attribution_10a51057.plan.md`](/Users/rosario/.cursor/plans/compass_track_g_hop_reward_attribution_10a51057.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_g_hop_reward_attribution_10a51057.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_g_hop_reward_attribution_10a51057.plan.md) |
| H | Session polish CC-9/CC-6 | [`/Users/rosario/work/.cursor/plans/compass_track_h_session_polish_cc9_cc6_a9d611b2.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_h_session_polish_cc9_cc6_a9d611b2.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_h_session_polish_cc9_cc6_a9d611b2.plan.md`](/Users/rosario/.cursor/plans/compass_track_h_session_polish_cc9_cc6_a9d611b2.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_h_session_polish_cc9_cc6_a9d611b2.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_h_session_polish_cc9_cc6_a9d611b2.plan.md) |
| I | Plan hygiene | [`/Users/rosario/work/.cursor/plans/compass_track_i_plan_hygiene_9dd2800c.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_i_plan_hygiene_9dd2800c.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_i_plan_hygiene_9dd2800c.plan.md`](/Users/rosario/.cursor/plans/compass_track_i_plan_hygiene_9dd2800c.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_i_plan_hygiene_9dd2800c.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_i_plan_hygiene_9dd2800c.plan.md) |
| J | Wasmer browser/mobile | [`/Users/rosario/work/.cursor/plans/compass_track_j_wasmer_browser_mobile_6086a6e5.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_j_wasmer_browser_mobile_6086a6e5.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_j_wasmer_browser_mobile_6086a6e5.plan.md`](/Users/rosario/.cursor/plans/compass_track_j_wasmer_browser_mobile_6086a6e5.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_j_wasmer_browser_mobile_6086a6e5.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_j_wasmer_browser_mobile_6086a6e5.plan.md) |
| K | Archive disposition | [`/Users/rosario/work/.cursor/plans/compass_track_k_archive_disposition_69873459.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_k_archive_disposition_69873459.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_k_archive_disposition_69873459.plan.md`](/Users/rosario/.cursor/plans/compass_track_k_archive_disposition_69873459.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_k_archive_disposition_69873459.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_k_archive_disposition_69873459.plan.md) |
| L | PyPI release | [`/Users/rosario/work/.cursor/plans/compass_track_l_pypi_release_43bd556a.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_l_pypi_release_43bd556a.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_l_pypi_release_43bd556a.plan.md`](/Users/rosario/.cursor/plans/compass_track_l_pypi_release_43bd556a.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_l_pypi_release_43bd556a.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_l_pypi_release_43bd556a.plan.md) |
| M | Probe credentials | [`/Users/rosario/work/.cursor/plans/compass_track_m_probe_credentials_acfb34f5.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_m_probe_credentials_acfb34f5.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_m_probe_credentials_acfb34f5.plan.md`](/Users/rosario/.cursor/plans/compass_track_m_probe_credentials_acfb34f5.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_m_probe_credentials_acfb34f5.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_m_probe_credentials_acfb34f5.plan.md) |
| N | Paid pillars | [`/Users/rosario/work/.cursor/plans/compass_track_n_paid_pillars_fae9b18d.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_n_paid_pillars_fae9b18d.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_n_paid_pillars_fae9b18d.plan.md`](/Users/rosario/.cursor/plans/compass_track_n_paid_pillars_fae9b18d.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_n_paid_pillars_fae9b18d.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_n_paid_pillars_fae9b18d.plan.md) |

### Phase 2 progress notes

- Track N paid pillars completed 2026-09-05 (PT): sync automation + fleet stub + governance hooks; `docs/gtm/PAID-SURFACES.md`; evidence `test-results/n-paid-pillars/`; Phase 2 test-ready exit gate flipped (≠ production).
- Track L PyPI release completed 2026-09-05 (PT): `compass-router` `0.1.0`; CHANGELOG + `docs/RELEASE.md`; sdist/wheel + twine check FULL; TestPyPI upload NOT_RUN (no token); release workflow stub; evidence `test-results/l-pypi-release/`.
- Track J Wasmer browser/mobile completed 2026-09-05 (PT): headless Playwright smoke FULL; desktop `wasmer/desktop/run-decide.sh` FULL; size-budget/parity green; mobile device farm NOT_RUN (`wasmer/mobile/NOT_RUN.md`); evidence `test-results/j-wasmer-packaging/`.
- Track H session polish (CC-9/CC-6) completed 2026-09-05 (PT): scripted harness + `docs/session/CC9-CC6-CHECKLIST.md` + evidence under `test-results/h-session-polish/` (live IDE optional; graded NOT_RUN for manual Chat).

### Phase 2 build order

**I hygiene ∥ K archive → M credentials → F live probe → G reward (parallel after F schema hooks) → H session polish → J wasmer packaging → L release → N paid pillars (after L + F) → test-ready exit gate.**

Repo-local copies + short index: [`/Users/rosario/work/comPASS/.cursor/plans/README.md`](/Users/rosario/work/comPASS/.cursor/plans/README.md)
## Archive / agent refuse rule (Track K)

Agents **must refuse** edits under:

- `/Users/rosario/work/CHAT-COMPRESSOR.archived-0.1.3` (and any `*.archived*` / 0.1.3 lab copy)
- Any attempt to merge 0.1.3 personal identifiers or absolute `/Users/rosario/...` paths into canonical `comPREssOR`

Canonical implementation target: `/Users/rosario/work/comPREssOR` only. See ADR 0002 and ADR 0003.

## Phase 3 — Browser agent + generic adapter

Browser-only Wasmer appliance (ADR 0005) and generic LLM adapter (ADR 0006).

| Track | Name | Cursor plan (work) | User plans | Repo copy |
| --- | --- | --- | --- | --- |
| O | Generic LLM adapter | [`/Users/rosario/work/.cursor/plans/compass_phase3_track_o_generic_adapter_a7c3e91f.plan.md`](/Users/rosario/work/.cursor/plans/compass_phase3_track_o_generic_adapter_a7c3e91f.plan.md) | [`/Users/rosario/.cursor/plans/compass_phase3_track_o_generic_adapter_a7c3e91f.plan.md`](/Users/rosario/.cursor/plans/compass_phase3_track_o_generic_adapter_a7c3e91f.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_phase3_track_o_generic_adapter_a7c3e91f.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_phase3_track_o_generic_adapter_a7c3e91f.plan.md) |
