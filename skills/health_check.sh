#!/usr/bin/env bash
# Health Check — Verifies the Catholic Knowledge Workshop is operational

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
pass() { echo -e "  ${GREEN}✓${NC} $*"; }
fail() { echo -e "  ${RED}✗${NC} $*"; }
warn() { echo -e "  ${YELLOW}!${NC} $*"; }

echo "Catholic Knowledge Workshop — Health Check"
echo "──────────────────────────────────────────"
errors=0

echo ""
echo "Ollama:"
if command -v ollama &>/dev/null; then
    pass "CLI installed"
else
    fail "CLI not found"; errors=$((errors + 1))
fi

if curl -sf http://localhost:11434/api/tags &>/dev/null; then
    pass "Server running"
else
    warn "Server not running (start with: ollama serve)"
fi

for model in qwen2.5-coder:32b nomic-embed-text; do
    if ollama list 2>/dev/null | grep -i "$model" > /dev/null 2>&1; then
        pass "Model: ${model}"
    else
        warn "Model missing: ${model} (run: ollama pull ${model})"
    fi
done

echo ""
echo "Workspace:"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for dir in kbmd/{scripture,magisterium,canonlaw,liturgy,fathers} outputs/{study-guides,timelines,comparisons} skills sources/raw sources/normalized; do
    if [[ -d "${SCRIPT_DIR}/${dir}" ]]; then
        pass "${dir}/"
    else
        fail "Missing: ${dir}/"; errors=$((errors + 1))
    fi
done

echo ""
echo "SovereignSpec:"
if command -v sovereignspec &>/dev/null; then
    pass "CLI installed"
    if [[ -f "${SCRIPT_DIR}/.sovereignspec/specs/catholic-knowledge-system.sspec" ]]; then
        pass "Spec file present"
    else
        warn "Spec file missing"
    fi
else
    warn "SovereignSpec not installed (run: uv tool install sovereignspec)"
fi

echo ""
echo "──────────────────────────────────────────"
if (( errors == 0 )); then
    echo -e "${GREEN}All checks passed.${NC}"
else
    echo -e "${RED}${errors} check(s) failed.${NC}"
fi
