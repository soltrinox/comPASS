#!/bin/bash
set -euo pipefail
cd /Users/rosario/work/comPASS
/usr/bin/git fetch origin main
/usr/bin/git stash push -u -m "wip-unrelated" -- test-results/j-wasmer-packaging/size-budget.json scripts/airgap_adapter_sim.py scripts/apply-browser-challenge.sh scripts/git_status_only.sh services/agy-bridge-gate-harden.tgz || true
/usr/bin/git checkout -B feat/docker-browser-challenge origin/main
/usr/bin/git add wasmer/browser/challenge.html wasmer/browser/challenge.js wasmer/browser/circuitLoader.js wasmer/browser/README.challenge.md services/browser-client/Dockerfile services/browser-client/nginx.conf docker-compose.yml docs/DOCKER.md
/usr/bin/git status -sb
/usr/bin/git commit -m "feat: Docker browser challenge client (Pass+-style)"
/usr/bin/git push -u origin HEAD
gh pr create --fill --title "feat: Docker browser challenge client" --body "Challenge-first UI on :8088 (handle/binary_url), digest-pin GitHub wasm, prove in-browser, ask agy-bridge :8791. docker compose up --build -d then open http://127.0.0.1:8088/"
gh pr view --json url,number -q .url
