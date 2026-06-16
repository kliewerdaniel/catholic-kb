#!/usr/bin/env bash
# Catholic Sovereign Knowledge Workshop — Bootstrap Installer
# Version: 1.0.0
# License: MIT

set -euo pipefail
trap 'echo -e "\n[ERROR] Bootstrap failed at line $LINENO. Check output above." >&2; exit 1' ERR

# ─── Configuration ───────────────────────────────────────────────────────────

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="${SCRIPT_DIR}/.bootstrap.log"
readonly REQUIRED_DISK_MB=2000
readonly OLLAMA_MODELS=("qwen2.5-coder:32b" "nomic-embed-text")

# ─── Logging ─────────────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log()    { echo -e "${BLUE}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
warn()   { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error()  { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"; }
success(){ echo -e "${GREEN}[OK]${NC}    $*" | tee -a "$LOG_FILE"; }

# ─── Banner ──────────────────────────────────────────────────────────────────

print_banner() {
    echo -e "${BLUE}"
    cat << 'BANNER'

  ╔══════════════════════════════════════════════════════╗
  ║   Catholic Sovereign Knowledge Workshop              ║
  ║   Bootstrap Installer v1.0.0                         ║
  ╚══════════════════════════════════════════════════════╝

BANNER
    echo -e "${NC}"
}

# ─── Pre-flight Checks ──────────────────────────────────────────────────────

check_disk_space() {
    local available_mb
    if [[ "$(uname)" == "Darwin" ]]; then
        available_mb=$(df -m "$SCRIPT_DIR" | awk 'NR==2{print $4}')
    else
        available_mb=$(df -m "$SCRIPT_DIR" | awk 'NR==2{print $4}')
    fi
    if (( available_mb < REQUIRED_DISK_MB )); then
        error "Insufficient disk space. Need ${REQUIRED_DISK_MB}MB, have ${available_mb}MB."
        exit 1
    fi
    success "Disk space OK (${available_mb}MB available)"
}

check_existing_install() {
    if [[ -f "${SCRIPT_DIR}/.bootstrap_complete" ]]; then
        warn "Bootstrap already completed. Re-running will overwrite existing setup."
        read -r -p "Continue? [y/N] " response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log "Aborted."
            exit 0
        fi
    fi
}

# ─── Dependency Installation ────────────────────────────────────────────────

install_homebrew() {
    if [[ "$(uname)" != "Darwin" ]]; then
        warn "Homebrew skipped (not macOS)."
        return
    fi
    if command -v brew &>/dev/null; then
        success "Homebrew already installed"
        return
    fi
    log "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Ensure brew is in PATH for this session
    eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv 2>/dev/null)"
    success "Homebrew installed"
}

install_ollama() {
    if command -v ollama &>/dev/null; then
        success "Ollama already installed ($(ollama --version 2>/dev/null || echo 'unknown version'))"
        return
    fi
    log "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    success "Ollama installed"
}

ensure_ollama_running() {
    if pgrep -x "ollama" &>/dev/null; then
        success "Ollama server already running"
        return
    fi
    log "Starting Ollama server..."
    ollama serve &>/dev/null &
    local retries=0
    while ! curl -sf http://localhost:11434/api/tags &>/dev/null; do
        retries=$((retries + 1))
        if (( retries > 30 )); then
            error "Ollama failed to start after 30s"
            exit 1
        fi
        sleep 1
    done
    success "Ollama server running"
}

pull_models() {
    log "Pulling required models (this may take a few minutes)..."
    for model in "${OLLAMA_MODELS[@]}"; do
        if ollama list 2>/dev/null | grep -q "$model"; then
            success "Model '$model' already present"
        else
            log "  Pulling ${model}..."
            ollama pull "$model"
            success "Model '$model' pulled"
        fi
    done
}

install_opencode() {
    if command -v opencode &>/dev/null; then
        success "opencode already installed"
        return
    fi
    log "Installing opencode..."
    if command -v brew &>/dev/null; then
        brew install charmbracelet/tap/opencode 2>/dev/null || warn "opencode brew install failed — install manually"
    else
        warn "opencode not found. Install from: https://github.com/anomalyco/opencode"
    fi
}

# ─── Workspace Creation ─────────────────────────────────────────────────────

create_workspace() {
    log "Creating workspace structure..."

    local dirs=(
        "kbmd/scripture"
        "kbmd/magisterium"
        "kbmd/canonlaw"
        "kbmd/liturgy"
        "kbmd/fathers"
        "kbmd/doctorate"
        "outputs/study-guides"
        "outputs/timelines"
        "outputs/comparisons"
        "outputs/doctrinal-briefs"
        "skills"
        "sources/raw"
        "sources/normalized"
        ".sovereignspec/specs"
        ".sovereignspec/tasks"
        ".sovereignspec/adr"
        ".sovereignspec/graph"
        ".sovereignspec/agents/opencode"
        ".sovereignspec/patterns"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "${SCRIPT_DIR}/${dir}"
    done

    success "Workspace directories created"
}

# ─── Skill Scripts ───────────────────────────────────────────────────────────

write_source_harvester() {
    cat > "${SCRIPT_DIR}/skills/catholic_source_harvest.sh" << 'HARVEST_EOF'
#!/usr/bin/env bash
# Catholic Source Harvester — Pulls authoritative Catholic documents
# Usage: ./skills/catholic_source_harvest.sh [category]
#   category: all | magisterium | canonlaw | fathers | scripture (default: all)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="${SCRIPT_DIR}/sources/raw"
CATEGORY="${1:-all}"

mkdir -p "$RAW_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[FETCH]${NC} $*"; }
warn() { echo -e "${YELLOW}[SKIP]${NC}  $*"; }

fetch_with_retry() {
    local url="$1" dest="$2" retries=3 attempt=0
    while (( attempt < retries )); do
        if curl -fsSL --max-time 30 "$url" -o "$dest" 2>/dev/null; then
            return 0
        fi
        attempt=$((attempt + 1))
        (( attempt < retries )) && sleep 2
    done
    return 1
}

fetch_magisterium() {
    log "Fetching Catechism of the Catholic Church index..."
    fetch_with_retry "https://www.vatican.va/archive/ENG0015/_INDEX.HTM" \
        "${RAW_DIR}/ccc_index.html" || warn "CCC index fetch failed"

    log "Fetching Vatican documents portal..."
    fetch_with_retry "https://www.vatican.va/content/vatican/en.html" \
        "${RAW_DIR}/vatican_portal.html" || warn "Vatican portal fetch failed"

    log "Fetching Vatican II documents index..."
    fetch_with_retry "https://www.vatican.va/archive/hist_councils/ii_vatican_council/index.htm" \
        "${RAW_DIR}/vatican_ii_index.html" || warn "Vatican II index fetch failed"

    # Key encyclicals
    local -A encyclicals=(
        ["humani_generis"]="https://www.vatican.va/content/pius-xii/en/encyclicals/documents/hf_p-xii_enc_12081950_humani-generis.html"
        ["humanae_vitae"]="https://www.vatican.va/content/paul-vi/en/encyclicals/documents/hf_p-vi_enc_25071968_humanae-vitae.html"
        ["evangelii_gaudium"]="https://www.vatican.va/content/francesco/en/encyclicals/documents/papa-francesco_20131124_evangelii-gaudium.html"
        ["laudato_si"]="https://www.vatican.va/content/francesco/en/encyclicals/documents/papa-francesco_20150524_laudato-si.html"
        ["fratelli_tutti"]="https://www.vatican.va/content/francesco/en/encyclicals/documents/papa-francesco_20201003_fratelli-tutti.html"
    )
    mkdir -p "${RAW_DIR}/encyclicals"
    for name in "${!encyclicals[@]}"; do
        log "  Fetching encyclical: ${name}..."
        fetch_with_retry "${encycyclicals[$name]}" "${RAW_DIR}/encyclicals/${name}.html" \
            || warn "  Failed: ${name}"
    done
}

fetch_canon_law() {
    log "Fetching Code of Canon Law index..."
    fetch_with_retry "https://www.vatican.va/archive/cod-iuris-canonici/cic_index_en.html" \
        "${RAW_DIR}/canon_law_index.html" || warn "Canon Law index fetch failed"
}

fetch_fathers() {
    log "Fetching New Advent Church Fathers index..."
    fetch_with_retry "https://www.newadvent.org/fathers/" \
        "${RAW_DIR}/fathers_index.html" || warn "Fathers index fetch failed"

    log "Fetching New Advent Scholastics index..."
    fetch_with_retry "https://www.newadvent.org/summa/" \
        "${RAW_DIR}/summa_index.html" || warn "Summa index fetch failed"
}

fetch_scripture() {
    log "Fetching USCCB Bible readings index..."
    fetch_with_retry "https://www.usccb.org/bible/readings" \
        "${RAW_DIR}/usccb_readings.html" || warn "USCCB readings fetch failed"
}

case "$CATEGORY" in
    all)
        fetch_magisterium
        fetch_canon_law
        fetch_fathers
        fetch_scripture
        ;;
    magisterium) fetch_magisterium ;;
    canonlaw)    fetch_canon_law ;;
    fathers)     fetch_fathers ;;
    scripture)   fetch_scripture ;;
    *)           echo "Usage: $0 [all|magisterium|canonlaw|fathers|scripture]"; exit 1 ;;
esac

echo ""
log "Fetch complete. Raw sources saved to: ${RAW_DIR}"
log "Next step: run skills/build_kbmd_from_sources.sh"
HARVEST_EOF
    chmod +x "${SCRIPT_DIR}/skills/catholic_source_harvest.sh"
    success "Source harvester skill written"
}

write_kb_builder() {
    cat > "${SCRIPT_DIR}/skills/build_kbmd_from_sources.sh" << 'BUILD_EOF'
#!/usr/bin/env bash
# KBMD Builder — Converts raw HTML sources into structured markdown
# Usage: ./skills/build_kbmd_from_sources.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_DIR="${SCRIPT_DIR}/sources/raw"
NORM_DIR="${SCRIPT_DIR}/sources/normalized"
KBMD_DIR="${SCRIPT_DIR}/kbmd"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[BUILD]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }

mkdir -p "$NORM_DIR"

# Check for html2text or pandoc
HTML_CONVERTER=""
if command -v pandoc &>/dev/null; then
    HTML_CONVERTER="pandoc"
elif command -v html2text &>/dev/null; then
    HTML_CONVERTER="html2text"
else
    warn "Neither pandoc nor html2text found. Installing pandoc via brew..."
    if command -v brew &>/dev/null; then
        brew install pandoc
        HTML_CONVERTER="pandoc"
    else
        echo "ERROR: Install pandoc or html2text to continue."
        exit 1
    fi
fi

convert_html_to_md() {
    local input="$1" output="$2"
    case "$HTML_CONVERTER" in
        pandoc)    pandoc -f html -t markdown --wrap=none -o "$output" "$input" 2>/dev/null ;;
        html2text) html2text -width 120 -o "$output" "$input" 2>/dev/null ;;
    esac
}

# Process each raw source
count=0
if ls "${RAW_DIR}"/*.html 1>/dev/null 2>&1; then
    for html_file in "${RAW_DIR}"/*.html; do
        basename=$(basename "$html_file" .html)
        md_file="${NORM_DIR}/${basename}.md"
        log "Converting: ${basename}..."
        convert_html_to_md "$html_file" "$md_file"
        count=$((count + 1))
    done
fi

# Process subdirectories
for subdir in "${RAW_DIR}"/*/; do
    [[ -d "$subdir" ]] || continue
    subdir_name=$(basename "$subdir")
    mkdir -p "${NORM_DIR}/${subdir_name}"
    for html_file in "${subdir}"*.html; do
        [[ -f "$html_file" ]] || continue
        basename=$(basename "$html_file" .html)
        md_file="${NORM_DIR}/${subdir_name}/${basename}.md"
        log "Converting: ${subdir_name}/${basename}..."
        convert_html_to_md "$html_file" "$md_file"
        count=$((count + 1))
    done
done

log "Converted ${count} files to markdown."
log "NOTE: Full KBMD normalization (citation extraction, structure parsing)"
log "      is delegated to the agent reasoning layer."
log ""
log "Run 'sovereignspec spec compile catholic-knowledge-system' to continue."
BUILD_EOF
    chmod +x "${SCRIPT_DIR}/skills/build_kbmd_from_sources.sh"
    success "KB builder skill written"
}

write_health_check() {
    cat > "${SCRIPT_DIR}/skills/health_check.sh" << 'HEALTH_EOF'
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

# Check Ollama
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

for model in llama3.3:8b-instruct-q4_K_M nomic-embed-text; do
    if ollama list 2>/dev/null | grep -q "$model"; then
        pass "Model: ${model}"
    else
        warn "Model missing: ${model} (run: ollama pull ${model})"
    fi
done

# Check workspace
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

# Check sovereignspec
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
HEALTH_EOF
    chmod +x "${SCRIPT_DIR}/skills/health_check.sh"
    success "Health check skill written"
}

# ─── SovereignSpec Initialization ────────────────────────────────────────────

init_sovereignspec() {
    if ! command -v sovereignspec &>/dev/null; then
        warn "sovereignspec not found. Attempting install..."
        if command -v uv &>/dev/null; then
            uv tool install sovereignspec --from git+https://github.com/kliewerdaniel/sovereignSpec.git 2>/dev/null \
                || warn "sovereignspec install failed — install manually"
        else
            warn "uv not found. Install sovereignspec manually."
            return
        fi
    fi

    if [[ ! -d "${SCRIPT_DIR}/.sovereignspec" ]]; then
        log "Initializing sovereignspec..."
        cd "$SCRIPT_DIR" && sovereignspec init . --model qwen2.5-coder:32b 2>/dev/null \
            || warn "sovereignspec init failed — initialize manually"
    fi

    success "SovereignSpec initialized"
}

# ─── Config Files ────────────────────────────────────────────────────────────

write_env_file() {
    if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
        cat > "${SCRIPT_DIR}/.env" << 'ENV_EOF'
# Catholic Sovereign Knowledge Workshop — Environment
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.3:8b-instruct-q4_K_M
OLLAMA_EMBED_MODEL=nomic-embed-text
KBMD_DIR=./kbmd
OUTPUTS_DIR=./outputs
SOURCES_DIR=./sources
ENV_EOF
        success ".env file created"
    fi
}

write_gitignore() {
    if [[ ! -f "${SCRIPT_DIR}/.gitignore" ]]; then
        cat > "${SCRIPT_DIR}/.gitignore" << 'GIT_EOF'
# Dependencies
node_modules/
.venv/
__pycache__/

# Ollama
*.gguf

# Raw sources (large, re-downloadable)
sources/raw/

# Generated outputs (regenerable)
outputs/

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db

# Logs
*.log
.bootstrap.log
GIT_EOF
        success ".gitignore created"
    fi
}

# ─── Git Initialization ──────────────────────────────────────────────────────

init_git() {
    if [[ -d "${SCRIPT_DIR}/.git" ]]; then
        success "Git repository already initialized"
        return
    fi
    log "Initializing git repository..."
    cd "$SCRIPT_DIR" && git init -q
    success "Git repository initialized"
}

# ─── Main ────────────────────────────────────────────────────────────────────

main() {
    print_banner

    # Initialize log
    echo "Bootstrap started: $(date)" > "$LOG_FILE"

    # Pre-flight
    log "Running pre-flight checks..."
    check_disk_space
    check_existing_install

    # Install dependencies
    log "Installing dependencies..."
    install_homebrew
    install_ollama
    ensure_ollama_running
    pull_models
    install_opencode

    # Create workspace
    create_workspace

    # Write skills
    log "Writing skill scripts..."
    write_source_harvester
    write_kb_builder
    write_health_check

    # Initialize sovereignspec
    init_sovereignspec

    # Config files
    write_env_file
    write_gitignore
    init_git

    # Mark complete
    touch "${SCRIPT_DIR}/.bootstrap_complete"

    # Done
    echo ""
    echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Bootstrap complete!${NC}"
    echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Next steps:"
    echo "    1. Run the source harvester:"
    echo "         ./skills/catholic_source_harvest.sh"
    echo ""
    echo "    2. Build the knowledge base:"
    echo "         ./skills/build_kbmd_from_sources.sh"
    echo ""
    echo "    3. Compile the sovereignspec:"
    echo "         sovereignspec spec compile catholic-knowledge-system"
    echo ""
    echo "    4. Start reasoning:"
    echo "         opencode"
    echo ""
    echo "  Health check: ./skills/health_check.sh"
    echo ""
}

main "$@"
