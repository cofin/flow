#!/usr/bin/env bash
#
# Flow Framework - Intelligent Installer
#
# Installs Flow commands and skills for supported AI CLI tools:
# - Claude Code (~/.claude/)
# - Codex CLI (~/.codex/)
# - OpenCode (~/.config/opencode/)
#
# Features:
# - Detects existing configurations
# - Backs up before modifying
# - Merges intelligently (doesn't overwrite)
# - Installs only for detected/selected CLIs

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory (where flow templates are)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/templates"
BACKUP_DIR="$HOME/.flow-backup-$(date +%Y%m%d-%H%M%S)"

# CLI paths
CLAUDE_DIR="$HOME/.claude"
CODEX_DIR="$HOME/.codex"
OPENCODE_DIR="$HOME/.config/opencode"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Flow Framework - Intelligent Installer             ║"
echo "║                       Version 0.3.2                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

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

# Check if a command has conflicting name
has_command_conflict() {
    local target_dir="$1"
    local command_name="$2"

    if [[ -f "$target_dir/$command_name" ]]; then
        # Check if it's a flow command (has Flow header)
        if grep -q "Flow" "$target_dir/$command_name" 2>/dev/null; then
            return 1  # No conflict, it's our own file
        fi
        return 0  # Conflict with non-flow file
    fi
    return 1  # No conflict
}

# Merge or install a command file
install_command() {
    local source="$1"
    local target="$2"
    local name="$(basename "$source")"

    if [[ -f "$target" ]]; then
        if grep -q "Flow" "$target" 2>/dev/null; then
            # Existing Flow file - update it
            cp "$source" "$target"
            log_success "Updated: $name"
        else
            # Conflict with non-Flow file
            log_warn "Skipped $name (conflict with existing non-Flow command)"
            echo "         Existing: $target"
            echo "         To install: rename existing file and re-run"
        fi
    else
        cp "$source" "$target"
        log_success "Installed: $name"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# CLI Detection
# ─────────────────────────────────────────────────────────────────────────────

detect_clis() {
    echo ""
    echo -e "${CYAN}Detecting installed CLIs...${NC}"
    echo ""

    CLAUDE_INSTALLED=false
    CODEX_INSTALLED=false
    OPENCODE_INSTALLED=false

    # Claude Code
    if command -v claude &> /dev/null || [[ -d "$CLAUDE_DIR" ]]; then
        CLAUDE_INSTALLED=true
        log_success "Claude Code detected"
        [[ -d "$CLAUDE_DIR/commands" ]] && echo "         Existing commands: $(ls -1 "$CLAUDE_DIR/commands" 2>/dev/null | wc -l)"
        [[ -d "$CLAUDE_DIR/skills" ]] && echo "         Existing skills: $(ls -1 "$CLAUDE_DIR/skills" 2>/dev/null | wc -l)"
    else
        log_info "Claude Code not detected"
    fi

    # Codex CLI
    if command -v codex &> /dev/null || [[ -d "$CODEX_DIR" ]]; then
        CODEX_INSTALLED=true
        log_success "Codex CLI detected"
        [[ -d "$CODEX_DIR/prompts" ]] && echo "         Existing prompts: $(ls -1 "$CODEX_DIR/prompts" 2>/dev/null | wc -l)"
    else
        log_info "Codex CLI not detected"
    fi

    # OpenCode
    if command -v opencode &> /dev/null || [[ -d "$OPENCODE_DIR" ]]; then
        OPENCODE_INSTALLED=true
        log_success "OpenCode detected"
        [[ -d "$OPENCODE_DIR/commands" ]] && echo "         Existing commands: $(ls -1 "$OPENCODE_DIR/commands" 2>/dev/null | wc -l)"
    else
        log_info "OpenCode not detected"
    fi

    echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Claude Code Installation
# ─────────────────────────────────────────────────────────────────────────────

install_claude() {
    echo ""
    echo -e "${CYAN}Installing Flow for Claude Code...${NC}"
    echo ""

    # Create directories
    mkdir -p "$CLAUDE_DIR/commands"
    mkdir -p "$CLAUDE_DIR/skills"

    # Backup existing
    backup_dir "$CLAUDE_DIR/commands"
    backup_dir "$CLAUDE_DIR/skills"

    # Install commands
    local commands_src="$TEMPLATES_DIR/claude/commands"
    local commands_dst="$CLAUDE_DIR/commands"

    if [[ -d "$commands_src" ]]; then
        for cmd in "$commands_src"/*.md; do
            [[ -f "$cmd" ]] && install_command "$cmd" "$commands_dst/$(basename "$cmd")"
        done
    fi

    # Install skills (merge with existing)
    local skills_src="$TEMPLATES_DIR/skills"
    local skills_dst="$CLAUDE_DIR/skills"

    if [[ -d "$skills_src" ]]; then
        for skill_dir in "$skills_src"/*/; do
            local skill_name="$(basename "$skill_dir")"
            local skill_dst="$skills_dst/$skill_name"

            if [[ -d "$skill_dst" ]]; then
                # Skill exists - check if it's ours
                if grep -q "Flow" "$skill_dst/SKILL.md" 2>/dev/null; then
                    # Update our skill
                    cp -r "$skill_dir"/* "$skill_dst/"
                    log_success "Updated skill: $skill_name"
                else
                    log_warn "Skipped skill $skill_name (conflict with existing)"
                fi
            else
                # New skill
                mkdir -p "$skill_dst"
                cp -r "$skill_dir"/* "$skill_dst/"
                log_success "Installed skill: $skill_name"
            fi
        done
    fi

    echo ""
    log_success "Claude Code installation complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# Codex CLI Installation
# ─────────────────────────────────────────────────────────────────────────────

install_codex() {
    echo ""
    echo -e "${CYAN}Installing Flow for Codex CLI...${NC}"
    echo ""

    # Create directories
    mkdir -p "$CODEX_DIR/prompts"
    mkdir -p "$CODEX_DIR/skills"

    # Backup existing
    backup_file "$CODEX_DIR/AGENTS.md"
    backup_dir "$CODEX_DIR/prompts"

    # Install AGENTS.md (merge if exists)
    local agents_src="$TEMPLATES_DIR/codex/AGENTS.md"
    local agents_dst="$CODEX_DIR/AGENTS.md"

    if [[ -f "$agents_dst" ]]; then
        if grep -q "Flow Framework" "$agents_dst" 2>/dev/null; then
            # Already has Flow - replace Flow section
            cp "$agents_src" "$agents_dst"
            log_success "Updated: AGENTS.md"
        else
            # Append Flow section
            echo "" >> "$agents_dst"
            echo "---" >> "$agents_dst"
            echo "" >> "$agents_dst"
            cat "$agents_src" >> "$agents_dst"
            log_success "Merged: AGENTS.md (appended Flow section)"
        fi
    else
        cp "$agents_src" "$agents_dst"
        log_success "Installed: AGENTS.md"
    fi

    # Install prompts
    local prompts_src="$TEMPLATES_DIR/codex/prompts"
    local prompts_dst="$CODEX_DIR/prompts"

    if [[ -d "$prompts_src" ]]; then
        for prompt in "$prompts_src"/*.md; do
            [[ -f "$prompt" ]] && install_command "$prompt" "$prompts_dst/$(basename "$prompt")"
        done
    fi

    # Install skills (beads and flow only for now)
    local skills_src="$TEMPLATES_DIR/skills"
    local skills_dst="$CODEX_DIR/skills"

    for skill_name in "flow" "beads"; do
        local skill_dir="$skills_src/$skill_name"
        if [[ -d "$skill_dir" ]]; then
            local skill_dst="$skills_dst/$skill_name"
            mkdir -p "$skill_dst"
            cp -r "$skill_dir"/* "$skill_dst/"
            log_success "Installed skill: $skill_name"
        fi
    done

    echo ""
    log_success "Codex CLI installation complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# OpenCode Installation
# ─────────────────────────────────────────────────────────────────────────────

install_opencode() {
    echo ""
    echo -e "${CYAN}Installing Flow for OpenCode...${NC}"
    echo ""

    # Create directories
    mkdir -p "$OPENCODE_DIR/agents"
    mkdir -p "$OPENCODE_DIR/commands"

    # Backup existing
    backup_file "$OPENCODE_DIR/opencode.json"
    backup_dir "$OPENCODE_DIR/agents"
    backup_dir "$OPENCODE_DIR/commands"

    # Install opencode.json (merge if exists)
    local config_src="$TEMPLATES_DIR/opencode/opencode.json"
    local config_dst="$OPENCODE_DIR/opencode.json"

    if [[ -f "$config_dst" ]]; then
        if grep -q '"flow"' "$config_dst" 2>/dev/null; then
            log_info "OpenCode config already has Flow - updating commands only"
        else
            log_warn "Existing opencode.json found - manual merge required"
            echo "         Source: $config_src"
            echo "         Target: $config_dst"
            echo "         Add the 'commands' and 'agents' sections manually"
        fi
    else
        cp "$config_src" "$config_dst"
        log_success "Installed: opencode.json"
    fi

    # Install agent
    local agent_src="$TEMPLATES_DIR/opencode/agents/flow.md"
    local agent_dst="$OPENCODE_DIR/agents/flow.md"

    if [[ -f "$agent_src" ]]; then
        cp "$agent_src" "$agent_dst"
        log_success "Installed: agents/flow.md"
    fi

    # Install commands
    local commands_src="$TEMPLATES_DIR/opencode/commands"
    local commands_dst="$OPENCODE_DIR/commands"

    if [[ -d "$commands_src" ]]; then
        for cmd in "$commands_src"/*.md; do
            [[ -f "$cmd" ]] && install_command "$cmd" "$commands_dst/$(basename "$cmd")"
        done
    fi

    echo ""
    log_success "OpenCode installation complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# Beads Installation Check
# ─────────────────────────────────────────────────────────────────────────────

check_beads() {
    echo ""
    echo -e "${CYAN}Checking Beads CLI...${NC}"
    echo ""

    if command -v bd &> /dev/null; then
        local version=$(bd --version 2>/dev/null || echo "unknown")
        log_success "Beads CLI installed: $version"
    else
        log_warn "Beads CLI not found"
        echo ""
        echo "Flow requires Beads for cross-session memory."
        echo "Install with: npm install -g beads-cli"
        echo ""
        read -p "Install Beads now? [Y/n] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            npm install -g beads-cli
            log_success "Beads CLI installed"
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

main() {
    # Check templates exist
    if [[ ! -d "$TEMPLATES_DIR" ]]; then
        log_error "Templates directory not found: $TEMPLATES_DIR"
        log_error "Please run this script from the Flow repository"
        exit 1
    fi

    # Detect CLIs
    detect_clis

    # If none detected, ask which to install for
    if ! $CLAUDE_INSTALLED && ! $CODEX_INSTALLED && ! $OPENCODE_INSTALLED; then
        echo "No supported CLIs detected. Which would you like to install for?"
        echo ""
        echo "  1) Claude Code (~/.claude/)"
        echo "  2) Codex CLI (~/.codex/)"
        echo "  3) OpenCode (~/.config/opencode/)"
        echo "  4) All of the above"
        echo "  5) Exit"
        echo ""
        read -p "Select [1-5]: " -n 1 -r
        echo
        case $REPLY in
            1) CLAUDE_INSTALLED=true ;;
            2) CODEX_INSTALLED=true ;;
            3) OPENCODE_INSTALLED=true ;;
            4) CLAUDE_INSTALLED=true; CODEX_INSTALLED=true; OPENCODE_INSTALLED=true ;;
            5) exit 0 ;;
        esac
    else
        # Ask which detected CLIs to install for
        echo "Which CLIs would you like to install Flow for?"
        echo ""
        $CLAUDE_INSTALLED && echo "  1) Claude Code"
        $CODEX_INSTALLED && echo "  2) Codex CLI"
        $OPENCODE_INSTALLED && echo "  3) OpenCode"
        echo "  a) All detected"
        echo "  q) Quit"
        echo ""
        read -p "Select (e.g., '1 2' or 'a'): " -r SELECTION

        case $SELECTION in
            q|Q) exit 0 ;;
            a|A) ;; # Install all
            *)
                # Parse selection
                INSTALL_CLAUDE=false
                INSTALL_CODEX=false
                INSTALL_OPENCODE=false
                for sel in $SELECTION; do
                    case $sel in
                        1) INSTALL_CLAUDE=true ;;
                        2) INSTALL_CODEX=true ;;
                        3) INSTALL_OPENCODE=true ;;
                    esac
                done
                $INSTALL_CLAUDE || CLAUDE_INSTALLED=false
                $INSTALL_CODEX || CODEX_INSTALLED=false
                $INSTALL_OPENCODE || OPENCODE_INSTALLED=false
                ;;
        esac
    fi

    # Install for selected CLIs
    $CLAUDE_INSTALLED && install_claude
    $CODEX_INSTALLED && install_codex
    $OPENCODE_INSTALLED && install_opencode

    # Check Beads
    check_beads

    # Summary
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
    $CLAUDE_INSTALLED && echo "     Claude Code: /flow-setup"
    $CODEX_INSTALLED && echo "     Codex CLI:   /flow:setup"
    $OPENCODE_INSTALLED && echo "     OpenCode:    /flow:setup"
    echo ""
    echo "  3. Create your first track:"
    $CLAUDE_INSTALLED && echo "     Claude Code: /flow-prd \"your feature description\""
    $CODEX_INSTALLED && echo "     Codex CLI:   /flow:prd \"your feature description\""
    $OPENCODE_INSTALLED && echo "     OpenCode:    /flow:prd \"your feature description\""
    echo ""
    echo "Documentation: https://github.com/your-org/flow"
    echo ""
}

# Run
main "$@"
