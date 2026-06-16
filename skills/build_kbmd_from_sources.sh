#!/usr/bin/env bash
# KBMD Builder — Runs the Python processor to build structured knowledge base
# Usage: ./skills/build_kbmd_from_sources.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[BUILD]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR]${NC} python3 is required but not found"
    exit 1
fi

log "Running KB processor..."
python3 "${SCRIPT_DIR}/skills/process_kb.py"

echo ""
log "Build complete. Knowledge base in: ${SCRIPT_DIR}/kbmd/"
log "Run './skills/health_check.sh' to verify."
