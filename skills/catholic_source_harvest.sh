#!/usr/bin/env bash
# Catholic Source Harvester — Downloads full authoritative Catholic documents
# Usage: ./skills/catholic_source_harvest.sh [category]
#   category: all | magisterium | canonlaw | fathers | liturgy (default: all)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="${SCRIPT_DIR}/sources/raw"
CATEGORY="${1:-all}"

mkdir -p "$RAW_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[FETCH]${NC} $*"; }
warn() { echo -e "${YELLOW}[SKIP]${NC}  $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; }

fetch() {
    local url="$1" dest="$2" label="$3"
    if [[ -f "$dest" ]] && [[ $(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest" 2>/dev/null) -gt 1000 ]]; then
        log "  ${label} — already downloaded"
        return 0
    fi
    log "  ${label}..."
    if curl -fsSL --max-time 60 "$url" -o "$dest" 2>/dev/null; then
        local size
        size=$(stat -f%z "$dest" 2>/dev/null || stat -c%s "$dest" 2>/dev/null)
        log "  ${label} — $(($size / 1024))KB"
    else
        warn "  ${label} — failed"
    fi
}

# ─── Magisterium: CCC, Canon Law, GIRM ──────────────────────────────────────

fetch_magisterium() {
    log "Fetching magisterial documents..."

    mkdir -p "${RAW_DIR}/encyclicals" "${RAW_DIR}/vatican_ii"

    # Catechism of the Catholic Church (full text, 2865 paragraphs)
    fetch "https://github.com/aseemsavio/catholicism-in-json/releases/download/v2.0.0/catechism.json" \
        "${RAW_DIR}/catechism.json" "Catechism of the Catholic Church"

    # Code of Canon Law (1983, full)
    fetch "https://github.com/aseemsavio/catholicism-in-json/releases/download/v2.0.0/canon.json" \
        "${RAW_DIR}/canon.json" "Code of Canon Law"

    # General Instruction of the Roman Missal
    fetch "https://github.com/aseemsavio/catholicism-in-json/releases/download/v2.0.0/girm.json" \
        "${RAW_DIR}/girm.json" "General Instruction of the Roman Missal"

    # Vatican II Documents (from Vatican.va)
    local V2_BASE="https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents"
    fetch "${V2_BASE}/vat-ii_const_19631204_sacrosanctum-concilium_en.html" \
        "${RAW_DIR}/vatican_ii/sacrosanctum_concilium.html" "Sacrosanctum Concilium"
    fetch "${V2_BASE}/vat-ii_cons_19641121_lumen-gentium_en.html" \
        "${RAW_DIR}/vatican_ii/lumen_gentium.html" "Lumen Gentium"
    fetch "${V2_BASE}/vat-ii_const_19651118_dei-verbum_en.html" \
        "${RAW_DIR}/vatican_ii/dei_verbum.html" "Dei Verbum"
    fetch "${V2_BASE}/vat-ii_cons_19651207_gaudium-et-spes_en.html" \
        "${RAW_DIR}/vatican_ii/gaudium_et_spes.html" "Gaudium et Spes"
    fetch "${V2_BASE}/vat-ii_decl_19651207_dignitatis-humanae_en.html" \
        "${RAW_DIR}/vatican_ii/dignitatis_humanae.html" "Dignitatis Humanae"
    fetch "${V2_BASE}/vat-ii_decree_19641121_unitatis-redintegratio_en.html" \
        "${RAW_DIR}/vatican_ii/unitatis_redintegratio.html" "Unitatis Redintegratio"
    fetch "${V2_BASE}/vat-ii_decree_19641121_orientalium-ecclesiarum_en.html" \
        "${RAW_DIR}/vatican_ii/orientalium_ecclesiarum.html" "Orientalium Ecclesiarum"
    fetch "${V2_BASE}/vat-ii_decree_19651028_perfectae-caritatis_en.html" \
        "${RAW_DIR}/vatican_ii/perfectae_caritatis.html" "Perfectae Caritatis"
    fetch "${V2_BASE}/vat-ii_decree_19651028_christus-dominus_en.html" \
        "${RAW_DIR}/vatican_ii/christus_dominus.html" "Christus Dominus"
    fetch "${V2_BASE}/vat-ii_decree_19651204_ad-gentes_en.html" \
        "${RAW_DIR}/vatican_ii/ad_gentes.html" "Ad Gentes"
}

# ─── Church Fathers (Schaff archive, full text zips) ────────────────────────

fetch_fathers() {
    log "Fetching Church Fathers (Schaff archive)..."
    mkdir -p "${RAW_DIR}/church_fathers"

    local BASE="https://web.archive.org/web/20010729000256/http://www.ccel.org/fathers"

    # Ante-Nicene Fathers (ANF) — 10 volumes
    local -a ANF_FILES=("01" "02" "03" "04" "05" "06" "07" "08" "10")
    for vol in "${ANF_FILES[@]}"; do
        local ecf_num=$((10#$vol))
        [[ "$vol" == "10" ]] && ecf_num=9
        fetch "${BASE}/ANF-${vol}/ECF$(printf '%02d' $ecf_num).ZIP" \
            "${RAW_DIR}/church_fathers/anf${vol}.zip" "ANF Volume ${vol}"
    done

    # Nicene and Post-Nicene Fathers, Series I (Augustine, Chrysostom)
    for i in 01 02 03 04 05; do
        local ecf_num=$((10#$i + 9))
        fetch "${BASE}/NPNF1-${i}/ECF$(printf '%02d' $ecf_num).ZIP" \
            "${RAW_DIR}/church_fathers/npnf1_${i}.zip" "NPNF1 Volume ${i}"
    done

    # Nicene and Post-Nicene Fathers, Series II (Eusebius, Athanasius, etc.)
    for i in 01 02 03 04; do
        local ecf_num=$((10#$i + 23))
        fetch "${BASE}/NPNF2-${i}/ECF$(printf '%02d' $ecf_num).ZIP" \
            "${RAW_DIR}/church_fathers/npnf2_${i}.zip" "NPNF2 Volume ${i}"
    done
}

# ─── Main ────────────────────────────────────────────────────────────────────

case "$CATEGORY" in
    all)
        fetch_magisterium
        fetch_fathers
        ;;
    magisterium) fetch_magisterium ;;
    fathers)     fetch_fathers ;;
    *)           echo "Usage: $0 [all|magisterium|fathers]"; exit 1 ;;
esac

echo ""
log "Fetch complete. Raw sources saved to: ${RAW_DIR}"
log "Next step: python3 skills/process_kb.py"
