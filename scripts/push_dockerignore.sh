#!/bin/bash
set -euo pipefail
cd /Users/rosario/work/comPASS
/usr/bin/git add .dockerignore
/usr/bin/git commit -m "chore: dockerignore for faster browser-client builds" || true
/usr/bin/git push
gh pr view 2 --json url,state
