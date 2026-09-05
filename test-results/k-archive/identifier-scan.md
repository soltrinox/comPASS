# Track K identifier scan — canonical source

**Recorded (UTC):** 2026-09-05T20:10:00Z
**Scope:** `engine/`, `extension/`, `scripts/`, `docs/` under comPREssOR and live CHAT-COMPRESSOR
**Patterns:** `FORBIDDEN_WORKSPACE`, `/Users/rosario`, word `rosario`

## Results

| Tree | Hits |
| --- | --- |
| comPREssOR | 0 |
| CHAT-COMPRESSOR (fresh clone) | 0 |

**Verdict:** CLEAN — no reintroduced 0.1.3 personal identifiers / absolute `/Users/rosario` paths in scanned source.

## Archive (expected dirty — not an implementation target)

Sample known 0.1.3 markers (truncated):

```
src/chat_compressor/live_models.py:20:FORBIDDEN_WORKSPACE = Path("/Users/rosario/work")
src/chat_compressor/graph.py:75: ... rosario ... (identifier regex)
scripts/scenario_press_release.py:38:WORKSPACE = Path("/Users/rosario/work")
scripts/run-press-release-layer-a.sh:5:LAB="/Users/rosario/work/CHAT-COMPRESSOR"
```
