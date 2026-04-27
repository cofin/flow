#!/usr/bin/env bash
#
# Flow Framework - Multi-host installer
#
# Thin orchestrator that runs each host's NATIVE plugin/extension command:
#   - Claude Code:  claude plugin marketplace add + plugin install
#   - Codex CLI:    codex plugin marketplace add
#   - Gemini CLI:   gemini extensions install --auto-update
#   - OpenCode:     symlink-based local plugin (no native marketplace)
#   - Antigravity:  skill copy (no native plugin system)
#
# Prefer the per-host native commands documented in README.md when installing
# into a single CLI. This script exists to install Flow across several hosts
# in one pass, and to clean up artifacts from older symlink-based installs.

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FLOW_GITHUB_REPO="https://github.com/cofin/flow"
FLOW_MARKETPLACE_SOURCE="cofin/flow"
FLOW_MARKETPLACE_NAME="flow-marketplace"
SKILLS_DIR="$PROJECT_ROOT/skills"
FLOW_DATA_DIR="$HOME/.flow"
BACKUP_DIR="$FLOW_DATA_DIR/backups/$(date +%Y%m%d-%H%M%S)"

FORCE_OVERWRITE=false

# Host paths
CLAUDE_DIR="$HOME/.claude"
CODEX_DIR="$HOME/.codex"
OPENCODE_DIR="$HOME/.config/opencode"
GEMINI_DIR="$HOME/.gemini"
ANTIGRAVITY_DIR="$HOME/.gemini/antigravity/skills"
JETSKI_DIR="$HOME/.jetski/skills"
GEMINI_JETSKI_DIR="$HOME/.gemini/jetski/skills"

show_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║             Flow Framework - Plugin Installer                ║"
    echo "║                       Version 0.20.3                         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    if $FORCE_OVERWRITE; then
        echo -e "${YELLOW}Mode: Force Overwrite${NC} (existing files will be replaced)"
        echo ""
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

backup_file() {
    local file="$1"
    if [[ -f "$file" ]]; then
        mkdir -p "$BACKUP_DIR"
        local rel_path="${file#$HOME/}"
        local backup_path="$BACKUP_DIR/$rel_path"
        mkdir -p "$(dirname "$backup_path")"
        cp "$file" "$backup_path"
        log_info "Backed up: $file"
    fi
}

backup_dir() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        mkdir -p "$BACKUP_DIR"
        local rel_path="${dir#$HOME/}"
        local backup_path="$BACKUP_DIR/$rel_path"
        mkdir -p "$(dirname "$backup_path")"
        cp -r "$dir" "$backup_path"
        log_info "Backed up: $dir"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Legacy cleanup — pre-marketplace symlink installs
# ─────────────────────────────────────────────────────────────────────────────

# Skill directory names from older installs that copied skills into per-host
# global skill directories (now superseded by plugin-managed skills).
FLOW_SKILL_DIRS=(
    advanced-alchemy alloydb alloydb-omni angular bash bd-to-br-migration
    biome bun cloud-run cpp dishka docker duckdb flow gcp gke htmx inertia
    ipc litestar makefile mojo mysql nuxt oracle podman postgres pyapp
    pytest-databases python railway react rust shadcn sphinx sqlalchemy
    sqlserver sqlspec svelte tailwind tanstack testing ty vite vue
)

cleanup_claude_legacy() {
    echo ""
    echo -e "${CYAN}Cleaning up legacy Claude Code installations...${NC}"
    echo ""

    local cleaned=false

    if [[ -d "$CLAUDE_DIR/skills" ]]; then
        for skill in "${FLOW_SKILL_DIRS[@]}"; do
            if [[ -d "$CLAUDE_DIR/skills/$skill" ]]; then
                rm -rf "$CLAUDE_DIR/skills/$skill"
                log_success "Removed legacy skill: ~/.claude/skills/$skill"
                cleaned=true
            fi
        done
        if [[ -d "$CLAUDE_DIR/skills" ]] && [[ -z "$(ls -A "$CLAUDE_DIR/skills" 2>/dev/null)" ]]; then
            rmdir "$CLAUDE_DIR/skills"
            log_success "Removed empty ~/.claude/skills/"
        fi
    fi

    if [[ -d "$CLAUDE_DIR/commands" ]]; then
        for cmd in "$CLAUDE_DIR/commands"/flow-*.md; do
            if [[ -f "$cmd" ]]; then
                rm -f "$cmd"
                log_success "Removed legacy command: $(basename "$cmd")"
                cleaned=true
            fi
        done
        if [[ -d "$CLAUDE_DIR/commands" ]] && [[ -z "$(ls -A "$CLAUDE_DIR/commands" 2>/dev/null)" ]]; then
            rmdir "$CLAUDE_DIR/commands"
            log_success "Removed empty ~/.claude/commands/"
        fi
    fi

    if [[ -d "$CLAUDE_DIR/hooks" ]]; then
        for hook_file in "hooks.json" "hooks-claude.json" "run-hook.cmd" "run-hook.sh" "session-start" "session-start.sh" "session-start.cmd" "session-start.ps1"; do
            if [[ -f "$CLAUDE_DIR/hooks/$hook_file" ]] && grep -q -i "flow\|beads\|bd " "$CLAUDE_DIR/hooks/$hook_file" 2>/dev/null; then
                rm -f "$CLAUDE_DIR/hooks/$hook_file"
                log_success "Removed legacy hook: $hook_file"
                cleaned=true
            fi
        done
        if [[ -d "$CLAUDE_DIR/hooks" ]] && [[ -z "$(ls -A "$CLAUDE_DIR/hooks" 2>/dev/null)" ]]; then
            rmdir "$CLAUDE_DIR/hooks"
            log_success "Removed empty ~/.claude/hooks/"
        fi
    fi

    $cleaned && log_success "Legacy Claude Code installation cleaned up" || log_info "No legacy Claude Code installation found"
}

cleanup_codex_legacy() {
    echo ""
    echo -e "${CYAN}Cleaning up legacy Codex installations...${NC}"
    echo ""

    local cleaned=false

    # Stale clone at ~/.codex/flow/
    if [[ -d "$CODEX_DIR/flow" ]]; then
        backup_dir "$CODEX_DIR/flow"
        rm -rf "$CODEX_DIR/flow"
        log_success "Removed stale clone: ~/.codex/flow/"
        cleaned=true
    fi

    # Pre-marketplace symlinked plugin at ~/.codex/plugins/flow
    if [[ -L "$CODEX_DIR/plugins/flow" ]]; then
        rm -f "$CODEX_DIR/plugins/flow"
        log_success "Removed pre-marketplace symlink: ~/.codex/plugins/flow"
        cleaned=true
    fi

    # Legacy global skills at ~/.codex/skills/
    if [[ -d "$CODEX_DIR/skills" ]]; then
        backup_dir "$CODEX_DIR/skills"
        rm -rf "$CODEX_DIR/skills"
        log_success "Removed stale skills: ~/.codex/skills/"
        cleaned=true
    fi

    # Old prompt files
    if ls "$CODEX_DIR/prompts/flow-"*.md &>/dev/null 2>&1; then
        rm -f "$CODEX_DIR/prompts/flow-"*.md
        log_success "Removed legacy prompts"
        cleaned=true
    fi

    # Old AGENTS.md Flow section
    if [[ -f "$CODEX_DIR/AGENTS.md" ]] && grep -q "Flow Framework" "$CODEX_DIR/AGENTS.md" 2>/dev/null; then
        backup_file "$CODEX_DIR/AGENTS.md"
        local tmp_file
        tmp_file=$(mktemp)
        sed '/^# Flow Framework/,$d' "$CODEX_DIR/AGENTS.md" > "$tmp_file"
        mv "$tmp_file" "$CODEX_DIR/AGENTS.md"
        tmp_file=$(mktemp)
        sed -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$CODEX_DIR/AGENTS.md" > "$tmp_file"
        mv "$tmp_file" "$CODEX_DIR/AGENTS.md"
        log_success "Removed legacy Flow section from AGENTS.md"
        cleaned=true
    fi

    $cleaned && log_success "Legacy Codex installation cleaned up" || log_info "No legacy Codex installation found"
}

cleanup_opencode_legacy() {
    echo ""
    echo -e "${CYAN}Cleaning up legacy OpenCode installations...${NC}"
    echo ""

    local cleaned=false

    if [[ -f "$OPENCODE_DIR/agents/flow.md" ]]; then
        rm -f "$OPENCODE_DIR/agents/flow.md"
        log_success "Removed legacy agents/flow.md"
        cleaned=true
    fi

    if ls "$OPENCODE_DIR/commands/flow-"*.md &>/dev/null 2>&1; then
        rm -f "$OPENCODE_DIR/commands/flow-"*.md
        log_success "Removed legacy command files"
        cleaned=true
    fi

    $cleaned && log_success "Legacy OpenCode installation cleaned up" || log_info "No legacy OpenCode installation found"
}

# ─────────────────────────────────────────────────────────────────────────────
# Host detection
# ─────────────────────────────────────────────────────────────────────────────

detect_clis() {
    echo ""
    echo -e "${CYAN}Detecting installed CLIs...${NC}"
    echo ""

    CLAUDE_INSTALLED=false
    CODEX_INSTALLED=false
    OPENCODE_INSTALLED=false
    GEMINI_INSTALLED=false
    ANTIGRAVITY_INSTALLED=false

    if command -v claude &>/dev/null || [[ -d "$CLAUDE_DIR" ]]; then
        CLAUDE_INSTALLED=true
        log_success "Claude Code detected"
    else
        log_info "Claude Code not detected"
    fi

    if command -v codex &>/dev/null || [[ -d "$CODEX_DIR" ]]; then
        CODEX_INSTALLED=true
        log_success "Codex CLI detected"
    else
        log_info "Codex CLI not detected"
    fi

    if command -v opencode &>/dev/null || [[ -d "$OPENCODE_DIR" ]]; then
        OPENCODE_INSTALLED=true
        log_success "OpenCode detected"
    else
        log_info "OpenCode not detected"
    fi

    if command -v gemini &>/dev/null || [[ -d "$GEMINI_DIR" ]]; then
        GEMINI_INSTALLED=true
        log_success "Gemini CLI detected"
    else
        log_info "Gemini CLI not detected"
    fi

    if command -v agy &>/dev/null || command -v jetski &>/dev/null \
       || [[ -d "$ANTIGRAVITY_DIR" ]] || [[ -d "$JETSKI_DIR" ]] || [[ -d "$GEMINI_JETSKI_DIR" ]]; then
        ANTIGRAVITY_INSTALLED=true
        log_success "Google Antigravity detected"
    else
        log_info "Google Antigravity not detected"
    fi

    echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Claude Code — native marketplace install
# ─────────────────────────────────────────────────────────────────────────────

install_claude() {
    echo ""
    echo -e "${CYAN}Installing Flow for Claude Code...${NC}"
    echo ""

    cleanup_claude_legacy

    if ! command -v claude &>/dev/null; then
        log_warn "claude binary not found in PATH"
        log_info "Install Flow by running these commands once Claude Code is installed:"
        echo "    claude plugin marketplace add $FLOW_MARKETPLACE_SOURCE"
        echo "    claude plugin install flow@$FLOW_MARKETPLACE_NAME"
        return
    fi

    log_info "Adding marketplace: $FLOW_MARKETPLACE_SOURCE"
    if ! claude plugin marketplace add "$FLOW_MARKETPLACE_SOURCE" >/dev/null 2>&1; then
        log_info "Marketplace add returned non-zero (likely already configured); continuing"
    else
        log_success "Marketplace registered"
    fi

    if claude plugin install "flow@$FLOW_MARKETPLACE_NAME" --scope user >/dev/null 2>&1; then
        log_success "Installed flow@$FLOW_MARKETPLACE_NAME (user scope)"
    elif claude plugin update "flow@$FLOW_MARKETPLACE_NAME" --scope user >/dev/null 2>&1; then
        log_success "Updated existing flow@$FLOW_MARKETPLACE_NAME install"
    else
        log_warn "Native install/update did not complete cleanly"
        log_info "Try manually:"
        echo "    claude plugin marketplace add $FLOW_MARKETPLACE_SOURCE"
        echo "    claude plugin install flow@$FLOW_MARKETPLACE_NAME"
        return
    fi

    echo ""
    log_success "Claude Code installation complete"
    log_info "To refresh later:"
    echo "    claude plugin marketplace update $FLOW_MARKETPLACE_NAME"
    echo "    claude plugin update flow@$FLOW_MARKETPLACE_NAME"
}

# ─────────────────────────────────────────────────────────────────────────────
# Codex CLI — native marketplace install
# ─────────────────────────────────────────────────────────────────────────────

install_codex() {
    echo ""
    echo -e "${CYAN}Installing Flow for Codex CLI...${NC}"
    echo ""

    cleanup_codex_legacy

    if ! command -v codex &>/dev/null; then
        log_warn "codex binary not found in PATH"
        log_info "Install Flow by running this command once Codex CLI is installed:"
        echo "    codex plugin marketplace add $FLOW_MARKETPLACE_SOURCE"
        log_info "Then enable Flow in a Codex session via /plugins"
        return
    fi

    log_info "Adding marketplace: $FLOW_MARKETPLACE_SOURCE"
    if codex plugin marketplace add "$FLOW_MARKETPLACE_SOURCE" >/dev/null 2>&1; then
        log_success "Marketplace registered"
    else
        log_info "Marketplace add returned non-zero (likely already configured); attempting upgrade"
        if codex plugin marketplace upgrade "$FLOW_MARKETPLACE_NAME" >/dev/null 2>&1; then
            log_success "Marketplace upgraded"
        else
            log_warn "codex plugin marketplace add/upgrade did not complete cleanly"
            log_info "Codex CLI 0.117+ is required for native marketplace commands."
            log_info "Verify with: codex --version"
            return
        fi
    fi

    echo ""
    log_success "Codex CLI installation complete"
    log_info "Open Codex and run: /plugins  → enable Flow"
    log_info "To refresh later:"
    echo "    codex plugin marketplace upgrade $FLOW_MARKETPLACE_NAME"
}

# ─────────────────────────────────────────────────────────────────────────────
# OpenCode — local plugin file (no native marketplace)
# ─────────────────────────────────────────────────────────────────────────────

install_opencode() {
    echo ""
    echo -e "${CYAN}Installing Flow for OpenCode...${NC}"
    echo ""

    cleanup_opencode_legacy

    local backing_dir="$OPENCODE_DIR/flow"
    local plugin_dir="$OPENCODE_DIR/plugins"
    local plugin_file="$plugin_dir/flow.js"
    local source_plugin="$backing_dir/.opencode/plugins/flow.js"

    if [[ -d "$backing_dir" && ! -L "$backing_dir" ]]; then
        backup_dir "$backing_dir"
        rm -rf "$backing_dir"
    elif [[ -L "$backing_dir" ]]; then
        rm "$backing_dir"
    fi

    mkdir -p "$plugin_dir"
    ln -sf "$PROJECT_ROOT" "$backing_dir"
    log_success "Linked Flow source to $backing_dir"

    if [[ -L "$plugin_file" || -f "$plugin_file" ]]; then
        rm -f "$plugin_file"
    fi
    ln -sf "$source_plugin" "$plugin_file"
    log_success "Linked plugin entrypoint to $plugin_file"

    echo ""
    log_success "OpenCode installation complete (local plugin file)"
    log_info "OpenCode auto-loads plugin files from ~/.config/opencode/plugins/"
    log_info "Project-local .agents/skills/ are also discovered automatically"
}

# ─────────────────────────────────────────────────────────────────────────────
# Gemini CLI — native extension install
# ─────────────────────────────────────────────────────────────────────────────

install_gemini() {
    echo ""
    echo -e "${CYAN}Installing Flow for Gemini CLI...${NC}"
    echo ""

    if ! command -v gemini &>/dev/null; then
        log_warn "gemini binary not found in PATH"
        log_info "Install Flow by running this command once Gemini CLI is installed:"
        echo "    gemini extensions install $FLOW_GITHUB_REPO --auto-update"
        return
    fi

    if gemini extensions install "$FLOW_GITHUB_REPO" --auto-update >/dev/null 2>&1; then
        log_success "Installed Flow extension with auto-update"
    elif gemini extensions update flow >/dev/null 2>&1; then
        log_success "Updated existing Flow extension"
    else
        log_warn "Native install/update did not complete cleanly"
        log_info "Try manually:"
        echo "    gemini extensions install $FLOW_GITHUB_REPO --auto-update"
        return
    fi

    echo ""
    log_success "Gemini CLI installation complete"
    log_info "Use 'gemini extensions link .' for local development against a checkout"
}

# ─────────────────────────────────────────────────────────────────────────────
# Google Antigravity — global skill copy (no native plugin system)
# ─────────────────────────────────────────────────────────────────────────────

install_antigravity() {
    echo ""
    echo -e "${CYAN}Installing Flow for Google Antigravity...${NC}"
    echo ""
    log_info "Prefer workspace-local .agents/rules and .agents/workflows when possible; this global install is a reusable fallback."

    local target_agy_dir="$ANTIGRAVITY_DIR"
    if [[ -d "$HOME/.jetski" ]]; then
        target_agy_dir="$JETSKI_DIR"
    elif [[ -d "$HOME/.gemini/jetski" ]]; then
        target_agy_dir="$GEMINI_JETSKI_DIR"
    fi

    if [[ -d "$target_agy_dir" ]]; then
        backup_dir "$target_agy_dir"
    fi

    mkdir -p "$target_agy_dir"

    if [[ -d "$SKILLS_DIR" ]]; then
        local count=0
        for skill_dir in "$SKILLS_DIR"/*/; do
            [[ -d "$skill_dir" ]] || continue
            local skill_name skill_dst_dir
            skill_name="$(basename "$skill_dir")"
            skill_dst_dir="$target_agy_dir/$skill_name"
            rm -rf "$skill_dst_dir"
            cp -r "$skill_dir" "$skill_dst_dir"
            count=$((count + 1))
        done
        log_success "Installed: $count skills"
    fi

    echo ""
    log_success "Google Antigravity installation complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# Beads installation check
# ─────────────────────────────────────────────────────────────────────────────

check_beads() {
    echo ""
    echo -e "${CYAN}Checking Beads CLI...${NC}"
    echo ""

    if command -v bd &>/dev/null; then
        local version
        version=$(bd --version 2>/dev/null || echo "unknown")
        log_success "Official Beads (bd) installed: $version"
        log_info "Flow setup will default to: bd init --non-interactive --stealth --prefix <repo-slug> --skip-agents"
        log_info "Flow setup will also set: bd config set no-git-ops true; bd config set export.auto false; bd config set export.git-add false"
        if command -v br &>/dev/null; then
            log_warn "Legacy br (beads_rust) detected alongside bd. Flow no longer uses br; you can uninstall it."
        fi
        return
    fi

    if command -v br &>/dev/null; then
        log_warn "Legacy br (beads_rust) detected. Flow no longer supports br."
        log_info "Install official Beads (bd) to enable Flow's task persistence."
    fi

    log_warn "No official Beads CLI (bd) detected"
    echo ""
    echo "Flow supports two persistence modes:"
    echo "  1) Install official Beads (bd) (recommended)"
    echo "  2) Continue without Beads"
    echo ""
    echo "Official install options: brew install beads, npm install -g @beads/bd,"
    echo "go install github.com/gastownhall/beads/cmd/bd@latest, or the installer script."
    echo ""
    read -p "Select [1-2]: " -n 1 -r
    echo
    case $REPLY in
        1)
            curl -fsSL https://raw.githubusercontent.com/gastownhall/beads/main/scripts/install.sh | bash
            log_success "Installed official Beads (bd)"
            log_info "Flow setup defaults to repo-slug prefixes and prefers .git/info/exclude for local-only artifacts"
            ;;
        *)
            log_info "Continuing without Beads; Flow will still support specs, plans, docs, and lightweight local workflows"
            ;;
    esac
}

# ─────────────────────────────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────────────────────────────

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force|--overwrite)
                FORCE_OVERWRITE=true
                shift
                ;;
            --help|-h)
                cat <<EOF
Usage: install.sh [OPTIONS]

Multi-host installer for the Flow Framework. Runs each host's NATIVE plugin
or extension command. For installing into a single host, prefer the per-host
commands documented in README.md.

Options:
  --force    Overwrite existing plugin installations without prompting
  --help     Show this help message
EOF
                exit 0
                ;;
            *)
                log_warn "Unknown option: $1"
                shift
                ;;
        esac
    done
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

main() {
    parse_args "$@"
    show_banner
    mkdir -p "$FLOW_DATA_DIR"
    detect_clis

    if ! $CLAUDE_INSTALLED && ! $CODEX_INSTALLED && ! $OPENCODE_INSTALLED && ! $GEMINI_INSTALLED && ! $ANTIGRAVITY_INSTALLED; then
        echo "No supported CLIs detected. Which would you like to install for?"
        echo ""
        echo "  1) Claude Code"
        echo "  2) Codex CLI"
        echo "  3) OpenCode"
        echo "  4) Gemini CLI"
        echo "  5) Google Antigravity"
        echo "  6) All of the above"
        echo "  7) Exit"
        echo ""
        read -p "Select [1-7]: " -n 1 -r
        echo
        case $REPLY in
            1) CLAUDE_INSTALLED=true ;;
            2) CODEX_INSTALLED=true ;;
            3) OPENCODE_INSTALLED=true ;;
            4) GEMINI_INSTALLED=true ;;
            5) ANTIGRAVITY_INSTALLED=true ;;
            6) CLAUDE_INSTALLED=true; CODEX_INSTALLED=true; OPENCODE_INSTALLED=true; GEMINI_INSTALLED=true; ANTIGRAVITY_INSTALLED=true ;;
            7) exit 0 ;;
        esac
    else
        echo "Which CLIs would you like to install Flow for?"
        echo ""
        $CLAUDE_INSTALLED && echo "  1) Claude Code"
        $CODEX_INSTALLED && echo "  2) Codex CLI"
        $OPENCODE_INSTALLED && echo "  3) OpenCode"
        $GEMINI_INSTALLED && echo "  4) Gemini CLI"
        $ANTIGRAVITY_INSTALLED && echo "  5) Google Antigravity"
        echo "  a) All detected"
        echo "  q) Quit"
        echo ""
        read -p "Select (e.g., '1 2' or 'a'): " -r SELECTION

        case $SELECTION in
            q|Q) exit 0 ;;
            a|A) ;; # all detected
            *)
                local install_claude=false install_codex=false install_opencode=false install_gemini=false install_antigravity=false
                for sel in $SELECTION; do
                    case $sel in
                        1) install_claude=true ;;
                        2) install_codex=true ;;
                        3) install_opencode=true ;;
                        4) install_gemini=true ;;
                        5) install_antigravity=true ;;
                    esac
                done
                $install_claude       || CLAUDE_INSTALLED=false
                $install_codex        || CODEX_INSTALLED=false
                $install_opencode     || OPENCODE_INSTALLED=false
                $install_gemini       || GEMINI_INSTALLED=false
                $install_antigravity  || ANTIGRAVITY_INSTALLED=false
                ;;
        esac
    fi

    $CLAUDE_INSTALLED       && install_claude
    $CODEX_INSTALLED        && install_codex
    $OPENCODE_INSTALLED     && install_opencode
    $GEMINI_INSTALLED       && install_gemini
    $ANTIGRAVITY_INSTALLED  && install_antigravity

    check_beads

    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Installation Complete!${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo ""

    if [[ -d "$BACKUP_DIR" ]]; then
        echo "Backups saved to: $BACKUP_DIR"
        echo ""
    fi

    echo "Next steps:"
    echo ""
    echo "  1. Navigate to your project:"
    echo "     cd /path/to/your/project"
    echo ""
    echo "  2. Initialize Flow:"
    $CLAUDE_INSTALLED       && echo "     Claude Code:        /flow-setup"
    $CODEX_INSTALLED        && echo "     Codex CLI:          Use Flow to set up this project"
    $OPENCODE_INSTALLED     && echo "     OpenCode:           /flow:setup"
    $GEMINI_INSTALLED       && echo "     Gemini CLI:         /flow:setup"
    $ANTIGRAVITY_INSTALLED  && echo "     Google Antigravity: flow-setup (skill)"
    echo ""
    echo "  3. Create your first flow:"
    $CLAUDE_INSTALLED       && echo "     Claude Code:        /flow-prd \"your feature description\""
    $CODEX_INSTALLED        && echo "     Codex CLI:          Use Flow to create a PRD for <feature>"
    $OPENCODE_INSTALLED     && echo "     OpenCode:           /flow:prd \"your feature description\""
    $GEMINI_INSTALLED       && echo "     Gemini CLI:         /flow:prd \"your feature description\""
    $ANTIGRAVITY_INSTALLED  && echo "     Google Antigravity: flow-prd \"your feature description\""
    echo ""
    echo "Documentation: https://github.com/cofin/flow"
    echo ""
}

main "$@"
