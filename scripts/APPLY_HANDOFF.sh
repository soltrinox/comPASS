#!/bin/bash
set -euo pipefail
ROOT="${1:-/Users/rosario/work/comPASS}"
PACK="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$ROOT/.cursor/plans" "$ROOT/docs"
cp -f "$PACK/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md" "$ROOT/.cursor/plans/"
cp -f "$PACK/docs/CURSOR-HANDOFF.md" "$ROOT/docs/"

# Sync to Cursor plan mirrors
for D in /Users/rosario/work/.cursor/plans /Users/rosario/.cursor/plans; do
  mkdir -p "$D"
  cp -f "$PACK/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md" "$D/"
done

# Patch PLANS.md Phase 3 table if status row missing
python3 - <<'PY'
from pathlib import Path
root = Path("/Users/rosario/work/comPASS")
plans = root / "PLANS.md"
text = plans.read_text()
# bump date header
text2 = text.replace("**Date:** 2026-09-05", "**Date:** 2026-09-07", 1)
if "compass_phase3_status_handoff_20260907" not in text2:
    needle = "| O | Generic LLM adapter |"
    idx = text2.find(needle)
    if idx < 0:
        raise SystemExit("O row missing")
    # find end of O table row
    line_end = text2.find("\n", idx)
    row = text2[idx:line_end]
    status_row = "| P3 Status | Phase 3 status handoff (Grok→Cursor) | [`/Users/rosario/work/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md`](/Users/rosario/work/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md) | [`/Users/rosario/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md`](/Users/rosario/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md) | [`/Users/rosario/work/comPASS/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md`](/Users/rosario/work/comPASS/.cursor/plans/compass_phase3_status_handoff_20260907.plan.md) |"
    text2 = text2[:line_end+1] + status_row + "\n" + text2[line_end+1:]
    notes = '''
### Phase 3 progress notes (2026-09-07 PT)

- **Handoff:** [`docs/CURSOR-HANDOFF.md`](docs/CURSOR-HANDOFF.md) — open first in Cursor after leaving Grok Bot.
- **Audit:** [`docs/AUDIT-GOALS-VS-BROWSER-STACK.md`](docs/AUDIT-GOALS-VS-BROWSER-STACK.md); stack map [`docs/WASMER-DEPLOYMENT.md`](docs/WASMER-DEPLOYMENT.md).
- Track O generic adapter **completed** (ADR 0006 / `src/compass/serve/adapter.py` + tests).
- ADRs **0005** (browser ENI6MA agent), **0007** (agy behind Gate) Accepted; agy-bridge + Compose on `:8791`.
- **PR #2** Docker `browser-client` challenge UI on `:8088` (handle / binary_url → digest-pin → minimal proof → Ask Gate) — merge + smoke still open.
- **Outstanding:** six-color ceremony UX, verify+burn ledger, full agent boot page, real comPREssOR hop inject, live-agy optional.
'''
    if "Phase 3 progress notes" not in text2:
        text2 = text2.rstrip() + "\n" + notes + "\n"
plans.write_text(text2)
print("PLANS.md updated")

readme = root / ".cursor/plans/README.md"
r = readme.read_text()
if "compass_phase3_status_handoff_20260907" not in r:
    if "## Phase 3" not in r:
        r = r.rstrip() + '''

## Phase 3 — Browser agent + status handoff

| Track | Plan |
| --- | --- |
| O — Generic LLM adapter | [compass_phase3_track_o_generic_adapter_a7c3e91f.plan.md](compass_phase3_track_o_generic_adapter_a7c3e91f.plan.md) |
| P3 Status — Grok→Cursor handoff | [compass_phase3_status_handoff_20260907.plan.md](compass_phase3_status_handoff_20260907.plan.md) |

Canonical narrative status: [`../../docs/CURSOR-HANDOFF.md`](../../docs/CURSOR-HANDOFF.md)
'''
    else:
        r = r.rstrip() + "\n| P3 Status — Grok→Cursor handoff | [compass_phase3_status_handoff_20260907.plan.md](compass_phase3_status_handoff_20260907.plan.md) |\n"
    readme.write_text(r + "\n")
    print("plans README updated")
else:
    print("plans README already has handoff")

# Link from docs/README.md
dread = root / "docs/README.md"
dt = dread.read_text()
if "CURSOR-HANDOFF.md" not in dt:
    needle = "| [`AUDIT-GOALS-VS-BROWSER-STACK.md`](AUDIT-GOALS-VS-BROWSER-STACK.md)"
    if needle in dt:
        row = "| [`CURSOR-HANDOFF.md`](CURSOR-HANDOFF.md) | **Cursor handoff (2026-09-07):** Phase 3 status, compose ports, PR #2, next todos |"
        # insert after AUDIT row - find full line
        import re
        m = re.search(r"\| \[`AUDIT-GOALS-VS-BROWSER-STACK\.md`\].*\n", dt)
        if m:
            dt = dt[:m.end()] + row + "\n" + dt[m.end():]
            dread.write_text(dt)
            print("docs README linked")
        else:
            print("AUDIT row regex miss")
    else:
        # insert after WASMER-DEPLOYMENT
        needle2 = "| [`WASMER-DEPLOYMENT.md`](WASMER-DEPLOYMENT.md) | **Phase 3 lifecycle:** zones A–D, Gate auth, adapter→bridge→agy, module maps, ports, operator cheat sheet |"
        if needle2 in dt:
            dt = dt.replace(needle2, needle2 + "\n| [`CURSOR-HANDOFF.md`](CURSOR-HANDOFF.md) | **Cursor handoff (2026-09-07):** Phase 3 status, compose ports, PR #2, next todos |")
            dread.write_text(dt)
            print("docs README linked via WASMER-DEPLOYMENT")
        else:
            print("docs README needle miss")
else:
    print("docs README already linked")
PY

# Ensure .dockerignore exists on branch
if [ ! -f "$ROOT/.dockerignore" ]; then
  cat > "$ROOT/.dockerignore" <<'DI'
.git
**/node_modules
**/.venv
**/__pycache__
**/*.pyc
test-results
**/target
**/.pytest_cache
**/dist
**/build
*.tgz
.env
.env.*
DI
fi

echo "Applied handoff into $ROOT"
