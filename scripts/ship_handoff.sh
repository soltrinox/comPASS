#!/bin/bash
set -euo pipefail
cd /Users/rosario/work/comPASS

# Sync plan mirrors
mkdir -p /Users/rosario/work/.cursor/plans /Users/rosario/.cursor/plans
cp -f .cursor/plans/compass_phase3_status_handoff_20260907.plan.md /Users/rosario/work/.cursor/plans/
cp -f .cursor/plans/compass_phase3_status_handoff_20260907.plan.md /Users/rosario/.cursor/plans/

python3 <<'PY'
from pathlib import Path
import re
root = Path("/Users/rosario/work/comPASS")
plans = root / "PLANS.md"
text = plans.read_text()
text2 = text.replace("**Date:** 2026-09-05", "**Date:** 2026-09-07", 1)
if "compass_phase3_status_handoff_20260907" not in text2:
    needle = "| O | Generic LLM adapter |"
    idx = text2.find(needle)
    if idx < 0:
        raise SystemExit("O row missing")
    line_end = text2.find("\n", idx)
    status_row = "| P3 Status | Phase 3 status handoff (Grok→Cursor) | [`/Users/rosario/work/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md`](/Users/rosario/work/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md) | [`/Users/rosario/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md`](/Users/rosario/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md) |"
    text2 = text2[:line_end+1] + status_row + "\n" + text2[line_end+1:]
if "Phase 3 progress notes" not in text2:
    notes = '''
### Phase 3 progress notes (2026-09-07 PT)

- **Handoff:** [`docs/CURSOR-HANDOFF.md`](docs/CURSOR-HANDOFF.md) — open first in Cursor after leaving Grok Bot.
- **Audit:** [`docs/AUDIT-GOALS-VS-BROWSER-STACK.md`](docs/AUDIT-GOALS-VS-BROWSER-STACK.md); stack map [`docs/WASMER-DEPLOYMENT.md`](docs/WASMER-DEPLOYMENT.md).
- Track O generic adapter **completed** (ADR 0006 / `src/compass/serve/adapter.py` + tests).
- ADRs **0005** (browser ENI6MA agent), **0007** (agy behind Gate) Accepted; agy-bridge + Compose on `:8791`.
- **PR #2** Docker `browser-client` challenge UI on `:8088` (handle / binary_url → digest-pin → minimal proof → Ask Gate) — merge + smoke still open.
- **Outstanding:** six-color ceremony UX, verify+burn ledger, full agent boot page, real comPREssOR hop inject, live-agy optional.
'''
    text2 = text2.rstrip() + "\n" + notes + "\n"
plans.write_text(text2)
print("PLANS.md ok")

readme = root / ".cursor/plans/README.md"
r = readme.read_text()
if "compass_phase3_status_handoff_20260907" not in r:
    block = '''
## Phase 3 — Browser agent + status handoff

| Track | Plan |
| --- | --- |
| O — Generic LLM adapter | [compass_phase3_track_o_generic_adapter_a7c3e91f.plan.md](compass_phase3_track_o_generic_adapter_a7c3e91f.plan.md) |
| P3 Status — Grok→Cursor handoff | [compass_phase3_status_handoff_20260907.plan.md](compass_phase3_status_handoff_20260907.plan.md) |

Canonical narrative status: [`../../docs/CURSOR-HANDOFF.md`](../../docs/CURSOR-HANDOFF.md)
'''
    if "## Phase 3" not in r:
        r = r.rstrip() + "\n" + block + "\n"
    else:
        r = r.rstrip() + "\n| P3 Status — Grok→Cursor handoff | [compass_phase3_status_handoff_20260907.plan.md](compass_phase3_status_handoff_20260907.plan.md) |\n"
    readme.write_text(r)
    print("plans README ok")

dread = root / "docs/README.md"
dt = dread.read_text()
if "CURSOR-HANDOFF.md" not in dt:
    row = "| [`CURSOR-HANDOFF.md`](CURSOR-HANDOFF.md) | **Cursor handoff (2026-09-07):** Phase 3 status, compose ports, PR #2, next todos |"
    m = re.search(r"\| \[`AUDIT-GOALS-VS-BROWSER-STACK\.md`\].*\n", dt)
    if m:
        dt = dt[:m.end()] + row + "\n" + dt[m.end():]
    else:
        needle2 = "| [`WASMER-DEPLOYMENT.md`](WASMER-DEPLOYMENT.md) | **Phase 3 lifecycle:** zones A–D, Gate auth, adapter→bridge→agy, module maps, ports, operator cheat sheet |"
        if needle2 not in dt:
            raise SystemExit("docs README insert failed")
        dt = dt.replace(needle2, needle2 + "\n" + row)
    dread.write_text(dt)
    print("docs README ok")

if not (root / ".dockerignore").exists():
    (root / ".dockerignore").write_text(".git\n**/node_modules\n**/.venv\n**/__pycache__\n**/*.pyc\ntest-results\n**/target\n**/.pytest_cache\n**/dist\n**/build\n*.tgz\n.env\n.env.*\n")
    print("dockerignore created")
PY

/usr/bin/git add \
  docs/CURSOR-HANDOFF.md \
  .cursor/plans/compass_phase3_status_handoff_20260907.plan.md \
  .cursor/plans/README.md \
  PLANS.md \
  docs/README.md \
  .dockerignore || true

/usr/bin/git status -sb
/usr/bin/git commit -m "docs: Cursor Phase 3 status handoff from Grok Bot"
/usr/bin/git push
gh pr comment 2 --body "Handoff for Cursor: \`docs/CURSOR-HANDOFF.md\` + \`.cursor/plans/compass_phase3_status_handoff_20260907.plan.md\` (also mirrored under ~/.cursor/plans and work/.cursor/plans). Open those first after switching from Grok Bot."
gh pr view 2 --json url,commits --jq '{url, last: .commits[-1].messageHeadline}'
