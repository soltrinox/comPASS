#!/usr/bin/env bash
# Discoverable validation entry for mobile Wasmer hosts (B4).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT/wasmer/mobile/run-hosts.sh"
