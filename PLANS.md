# comPASS program plans

**Date:** 2026-09-03  
**Ground truth:** [`/Users/rosario/work/comPASS/PROTOTYPE.md`](/Users/rosario/work/comPASS/PROTOTYPE.md)  
**Summary:** [`/Users/rosario/work/comPASS/SUMMARY/2026-09-03-comPASS-prototype-session.md`](/Users/rosario/work/comPASS/SUMMARY/2026-09-03-comPASS-prototype-session.md)  
**Canonical compressor:** `git@github.com:soltrinox/comPREssOR.git` at [`/Users/rosario/work/comPREssOR`](/Users/rosario/work/comPREssOR) (engine 0.2.0)

Each plan is registered in three places (identical bytes). Prefer the work copy when opening from this tree.

| Track | Name | Cursor plan (work) | User plans | Repo copy |
| --- | --- | --- | --- | --- |
| Master | comPASS Master Orchestration | [`/Users/rosario/work/.cursor/plans/compass_master_orchestration_b029ab33.plan.md`](/Users/rosario/work/.cursor/plans/compass_master_orchestration_b029ab33.plan.md) | [`/Users/rosario/.cursor/plans/compass_master_orchestration_b029ab33.plan.md`](/Users/rosario/.cursor/plans/compass_master_orchestration_b029ab33.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_master_orchestration_b029ab33.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_master_orchestration_b029ab33.plan.md) |
| A | comPASS Track A — Specs & Docs | [`/Users/rosario/work/.cursor/plans/compass_track_a_specs_docs_31e0c88a.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_a_specs_docs_31e0c88a.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_a_specs_docs_31e0c88a.plan.md`](/Users/rosario/.cursor/plans/compass_track_a_specs_docs_31e0c88a.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_a_specs_docs_31e0c88a.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_a_specs_docs_31e0c88a.plan.md) |
| B | comPASS Track B — Compressor Prerequisites | [`/Users/rosario/work/.cursor/plans/compass_track_b_compressor_prereqs_2f4c3239.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_b_compressor_prereqs_2f4c3239.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_b_compressor_prereqs_2f4c3239.plan.md`](/Users/rosario/.cursor/plans/compass_track_b_compressor_prereqs_2f4c3239.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_b_compressor_prereqs_2f4c3239.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_b_compressor_prereqs_2f4c3239.plan.md) |
| C | comPASS Track C — Sibling Engine | [`/Users/rosario/work/.cursor/plans/compass_track_c_sibling_engine_6b7641d9.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_c_sibling_engine_6b7641d9.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_c_sibling_engine_6b7641d9.plan.md`](/Users/rosario/.cursor/plans/compass_track_c_sibling_engine_6b7641d9.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_c_sibling_engine_6b7641d9.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_c_sibling_engine_6b7641d9.plan.md) |
| D | comPASS Track D — Wasmer Deployment | [`/Users/rosario/work/.cursor/plans/compass_track_d_wasmer_deploy_de4e7aa1.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_d_wasmer_deploy_de4e7aa1.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_d_wasmer_deploy_de4e7aa1.plan.md`](/Users/rosario/.cursor/plans/compass_track_d_wasmer_deploy_de4e7aa1.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_d_wasmer_deploy_de4e7aa1.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_d_wasmer_deploy_de4e7aa1.plan.md) |
| E | comPASS Track E — Product & GTM | [`/Users/rosario/work/.cursor/plans/compass_track_e_product_gtm_30bdaa6f.plan.md`](/Users/rosario/work/.cursor/plans/compass_track_e_product_gtm_30bdaa6f.plan.md) | [`/Users/rosario/.cursor/plans/compass_track_e_product_gtm_30bdaa6f.plan.md`](/Users/rosario/.cursor/plans/compass_track_e_product_gtm_30bdaa6f.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_track_e_product_gtm_30bdaa6f.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_track_e_product_gtm_30bdaa6f.plan.md) |

Repo-local copies + short index: [`/Users/rosario/work/comPASS/.cursor/plans/README.md`](/Users/rosario/work/comPASS/.cursor/plans/README.md)

## Build order

Track A → Track B M0/M1 → Track C scaffold/graph/route → Track D Wasmer cut → Track C tiers → Track E (ADRs for name and working-copy should close before public remote / compressor edits).
