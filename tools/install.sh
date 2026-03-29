#!/usr/bin/env bash
#
# Flow Framework - Plugin Installer
#
# Installs Flow as a plugin for supported AI CLI tools:
# - Claude Code (marketplace plugin via extraKnownMarketplaces)
# - Codex CLI (~/.codex/plugins/flow/)
# - OpenCode (~/.config/opencode/plugins/flow/)
# - Gemini CLI (~/.gemini/extensions/flow/)
# - Google Antigravity (~/.gemini/antigravity/skills/)
#
# All CLIs use their native plugin/extension system.
# No direct skill or command copying.

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory (where flow source is)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$PROJECT_ROOT/skills"
COMMANDS_DIR="$PROJECT_ROOT/commands"
FLOW_DATA_DIR="$HOME/.flow"
BACKUP_DIR="$FLOW_DATA_DIR/backups/$(date +%Y%m%d-%H%M%S)"

# Flags (parsed from command line)
FORCE_OVERWRITE=false

# CLI paths
CLAUDE_DIR="$HOME/.claude"
CODEX_DIR="$HOME/.codex"
OPENCODE_DIR="$HOME/.config/opencode"
GEMINI_DIR="$HOME/.gemini"
GEMINI_EXT_DIR="$GEMINI_DIR/extensions/flow"
ANTIGRAVITY_DIR="$HOME/.gemini/antigravity/skills"
JETSKI_DIR="$HOME/.jetski/skills"
GEMINI_JETSKI_DIR="$HOME/.gemini/jetski/skills"

show_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║             Flow Framework - Plugin Installer                ║"
    echo "║                       Version 0.12.2                         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    if $FORCE_OVERWRITE; then
        echo -e "${YELLOW}Mode: Force Overwrite${NC} (existing files will be replaced)"
        echo ""
    fi
}

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

# ─────────────────────────────────────────────────────────────────────────────
# Legacy Cleanup Functions
# ─────────────────────────────────────────────────────────────────────────────

# List of skill directory names that flow installs
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

    # Remove legacy skills from ~/.claude/skills/
    if [[ -d "$CLAUDE_DIR/skills" ]]; then
        for skill in "${FLOW_SKILL_DIRS[@]}"; do
            if [[ -d "$CLAUDE_DIR/skills/$skill" ]]; then
                rm -rf "$CLAUDE_DIR/skills/$skill"
                log_success "Removed legacy skill: ~/.claude/skills/$skill"
                cleaned=true
            fi
        done

        # Remove the skills dir if empty
        if [[ -d "$CLAUDE_DIR/skills" ]] && [[ -z "$(ls -A "$CLAUDE_DIR/skills" 2>/dev/null)" ]]; then
            rmdir "$CLAUDE_DIR/skills"
            log_success "Removed empty ~/.claude/skills/"
        fi
    fi

    # Remove legacy commands from ~/.claude/commands/
    if [[ -d "$CLAUDE_DIR/commands" ]]; then
        for cmd in "$CLAUDE_DIR/commands"/flow-*.md; do
            if [[ -f "$cmd" ]]; then
                rm -f "$cmd"
                log_success "Removed legacy command: $(basename "$cmd")"
                cleaned=true
            fi
        done

        # Remove the commands dir if empty
        if [[ -d "$CLAUDE_DIR/commands" ]] && [[ -z "$(ls -A "$CLAUDE_DIR/commands" 2>/dev/null)" ]]; then
            rmdir "$CLAUDE_DIR/commands"
            log_success "Removed empty ~/.claude/commands/"
        fi
    fi

    # Remove legacy hooks from ~/.claude/hooks/ (only if they are flow hooks)
    if [[ -d "$CLAUDE_DIR/hooks" ]]; then
        for hook_file in "hooks.json" "run-hook.cmd" "session-start"; do
            if [[ -f "$CLAUDE_DIR/hooks/$hook_file" ]] && grep -q -i "flow\|beads\|br sync" "$CLAUDE_DIR/hooks/$hook_file" 2>/dev/null; then
                rm -f "$CLAUDE_DIR/hooks/$hook_file"
                log_success "Removed legacy hook: $hook_file"
                cleaned=true
            fi
        done

        # Remove the hooks dir if empty
        if [[ -d "$CLAUDE_DIR/hooks" ]] && [[ -z "$(ls -A "$CLAUDE_DIR/hooks" 2>/dev/null)" ]]; then
            rmdir "$CLAUDE_DIR/hooks"
            log_success "Removed empty ~/.claude/hooks/"
        fi
    fi

    if $cleaned; then
        log_success "Legacy Claude Code installation cleaned up"
    else
        log_info "No legacy Claude Code installation found"
    fi
}

cleanup_codex_legacy() {
    echo ""
    echo -e "${CYAN}Cleaning up legacy Codex installations...${NC}"
    echo ""

    local cleaned=false

    # Remove stale git clone at ~/.codex/flow/
    if [[ -d "$CODEX_DIR/flow" ]]; then
        backup_dir "$CODEX_DIR/flow"
        rm -rf "$CODEX_DIR/flow"
        log_success "Removed stale clone: ~/.codex/flow/"
        cleaned=true
    fi

    # Remove stale skills at ~/.codex/skills/
    if [[ -d "$CODEX_DIR/skills" ]]; then
        backup_dir "$CODEX_DIR/skills"
        rm -rf "$CODEX_DIR/skills"
        log_success "Removed stale skills: ~/.codex/skills/"
        cleaned=true
    fi

    # Remove old prompts
    if ls "$CODEX_DIR/prompts/flow-"*.md &>/dev/null 2>&1; then
        rm -f "$CODEX_DIR/prompts/flow-"*.md
        log_success "Removed legacy prompts"
        cleaned=true
    fi

    # Remove Flow section from old AGENTS.md
    if [[ -f "$CODEX_DIR/AGENTS.md" ]] && grep -q "Flow Framework" "$CODEX_DIR/AGENTS.md" 2>/dev/null; then
        backup_file "$CODEX_DIR/AGENTS.md"
        sed -i '/^# Flow Framework/,$d' "$CODEX_DIR/AGENTS.md"
        sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$CODEX_DIR/AGENTS.md"
        log_success "Removed legacy Flow section from AGENTS.md"
        cleaned=true
    fi

    if $cleaned; then
        log_success "Legacy Codex installation cleaned up"
    else
        log_info "No legacy Codex installation found"
    fi
}

cleanup_opencode_legacy() {
    echo ""
    echo -e "${CYAN}Cleaning up legacy OpenCode installations...${NC}"
    echo ""

    local cleaned=false

    # Remove old agent files
    if [[ -f "$OPENCODE_DIR/agents/flow.md" ]]; then
        rm -f "$OPENCODE_DIR/agents/flow.md"
        log_success "Removed legacy agents/flow.md"
        cleaned=true
    fi

    # Remove old command files
    if ls "$OPENCODE_DIR/commands/flow-"*.md &>/dev/null 2>&1; then
        rm -f "$OPENCODE_DIR/commands/flow-"*.md
        log_success "Removed legacy command files"
        cleaned=true
    fi

    if $cleaned; then
        log_success "Legacy OpenCode installation cleaned up"
    else
        log_info "No legacy OpenCode installation found"
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
    GEMINI_INSTALLED=false
    ANTIGRAVITY_INSTALLED=false

    # Claude Code
    if command -v claude &> /dev/null || [[ -d "$CLAUDE_DIR" ]]; then
        CLAUDE_INSTALLED=true
        log_success "Claude Code detected"
    else
        log_info "Claude Code not detected"
    fi

    # Codex CLI
    if command -v codex &> /dev/null || [[ -d "$CODEX_DIR" ]]; then
        CODEX_INSTALLED=true
        log_success "Codex CLI detected"
    else
        log_info "Codex CLI not detected"
    fi

    # OpenCode
    if command -v opencode &> /dev/null || [[ -d "$OPENCODE_DIR" ]]; then
        OPENCODE_INSTALLED=true
        log_success "OpenCode detected"
    else
        log_info "OpenCode not detected"
    fi

    # Gemini CLI
    if command -v gemini &> /dev/null || [[ -d "$GEMINI_DIR" ]]; then
        GEMINI_INSTALLED=true
        log_success "Gemini CLI detected"
    else
        log_info "Gemini CLI not detected"
    fi

    # Google Antigravity
    if command -v agy &> /dev/null || command -v jetski &> /dev/null || [[ -d "$ANTIGRAVITY_DIR" ]] || [[ -d "$JETSKI_DIR" ]] || [[ -d "$GEMINI_JETSKI_DIR" ]]; then
        ANTIGRAVITY_INSTALLED=true
        log_success "Google Antigravity detected"
    else
        log_info "Google Antigravity not detected"
    fi

    echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Claude Code Installation (plugin via marketplace)
# ─────────────────────────────────────────────────────────────────────────────

install_claude() {
    echo ""
    echo -e "${CYAN}Installing Flow for Claude Code...${NC}"
    echo ""

    # Step 1: Clean up ALL legacy installations
    cleanup_claude_legacy

    # Step 2: Ensure settings.json has the marketplace entry
    local settings_file="$CLAUDE_DIR/settings.json"

    if [[ ! -f "$settings_file" ]]; then
        log_warn "No settings.json found at $settings_file"
        log_info "Create it or run: claude settings"
        echo ""
        log_info "Then add to settings.json:"
        echo '    "extraKnownMarketplaces": {'
        echo '      "flow-marketplace": {'
        echo '        "source": { "source": "github", "repo": "cofin/flow" }'
        echo '      }'
        echo '    }'
        echo ""
        echo '    "enabledPlugins": {'
        echo '      "flow@flow-marketplace": true'
        echo '    }'
        return
    fi

    # Check if marketplace entry exists
    if command -v jq &>/dev/null; then
        local has_marketplace
        has_marketplace=$(jq -r '.extraKnownMarketplaces."flow-marketplace" // empty' "$settings_file" 2>/dev/null)

        if [[ -z "$has_marketplace" ]]; then
            log_info "Adding flow-marketplace to settings.json..."
            backup_file "$settings_file"

            local tmp_file
            tmp_file=$(mktemp)
            jq '.extraKnownMarketplaces."flow-marketplace" = {"source": {"source": "github", "repo": "cofin/flow"}}' \
                "$settings_file" > "$tmp_file" && mv "$tmp_file" "$settings_file"
            log_success "Added extraKnownMarketplaces entry"
        else
            log_info "flow-marketplace already configured"
        fi

        # Check if plugin is enabled
        local is_enabled
        is_enabled=$(jq -r '.enabledPlugins."flow@flow-marketplace" // empty' "$settings_file" 2>/dev/null)

        if [[ -z "$is_enabled" ]]; then
            log_info "Enabling flow plugin..."
            local tmp_file
            tmp_file=$(mktemp)
            jq '.enabledPlugins."flow@flow-marketplace" = true' \
                "$settings_file" > "$tmp_file" && mv "$tmp_file" "$settings_file"
            log_success "Enabled flow@flow-marketplace"
        else
            log_info "flow@flow-marketplace already enabled"
        fi
    else
        # No jq — check with grep
        if ! grep -q "flow-marketplace" "$settings_file" 2>/dev/null; then
            log_warn "jq not available for automatic config update"
            echo ""
            log_info "Add to $settings_file:"
            echo '    "extraKnownMarketplaces": {'
            echo '      "flow-marketplace": {'
            echo '        "source": { "source": "github", "repo": "cofin/flow" }'
            echo '      }'
            echo '    }'
            echo ""
            echo '    "enabledPlugins": {'
            echo '      "flow@flow-marketplace": true'
            echo '    }'
        else
            log_info "flow-marketplace already configured"
        fi
    fi

    echo ""
    log_success "Claude Code installation complete (plugin via marketplace)"
    log_info "Claude Code will pull the latest version from GitHub on next start"
}

# ─────────────────────────────────────────────────────────────────────────────
# Codex CLI Installation (local plugin)
# ─────────────────────────────────────────────────────────────────────────────

install_codex() {
    echo ""
    echo -e "${CYAN}Installing Flow for Codex CLI...${NC}"
    echo ""

    # Step 1: Clean up ALL legacy installations
    cleanup_codex_legacy

    # Step 2: Install plugin at ~/.codex/plugins/flow/
    local plugin_dir="$HOME/.codex/plugins/flow"

    # Backup existing plugin if present
    if [[ -d "$plugin_dir" ]]; then
        backup_dir "$plugin_dir"
        rm -rf "$plugin_dir"
    fi

    # Create plugin directory
    mkdir -p "$plugin_dir"

    # Copy plugin manifest
    mkdir -p "$plugin_dir/.codex-plugin"
    cp "$PROJECT_ROOT/.codex-plugin/plugin.json" "$plugin_dir/.codex-plugin/"
    log_success "Installed: plugin manifest"

    # Copy AGENTS.md context
    cp "$PROJECT_ROOT/AGENTS.md" "$plugin_dir/"
    log_success "Installed: AGENTS.md"

    # Copy commands (Codex uses commands/flow/*.toml)
    mkdir -p "$plugin_dir/commands"
    cp -r "$COMMANDS_DIR/flow" "$plugin_dir/commands/"
    log_success "Installed: commands"

    # Copy hooks
    mkdir -p "$plugin_dir/hooks"
    cp "$PROJECT_ROOT/hooks/hooks-codex.json" "$plugin_dir/hooks/"
    cp "$PROJECT_ROOT/hooks/run-hook.cmd" "$plugin_dir/hooks/"
    cp "$PROJECT_ROOT/hooks/session-start" "$plugin_dir/hooks/"
    chmod +x "$plugin_dir/hooks/session-start" "$plugin_dir/hooks/run-hook.cmd"
    log_success "Installed: hooks"

    # Copy skills
    if [[ -d "$SKILLS_DIR" ]]; then
        cp -r "$SKILLS_DIR" "$plugin_dir/skills"
        log_success "Installed: skills ($(ls -1d "$SKILLS_DIR"/*/ 2>/dev/null | wc -l) skills)"
    fi

    # Step 3: Create or update marketplace.json
    local marketplace_dir="$HOME/.agents/plugins"
    local marketplace_file="$marketplace_dir/marketplace.json"
    mkdir -p "$marketplace_dir"

    if [[ ! -f "$marketplace_file" ]]; then
        cat > "$marketplace_file" << 'MARKETPLACE_EOF'
{
  "name": "personal-plugins",
  "interface": { "displayName": "Personal Plugins" },
  "plugins": [
    {
      "name": "flow",
      "source": { "source": "local", "path": "./.codex/plugins/flow" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Development"
    }
  ]
}
MARKETPLACE_EOF
        log_success "Created: marketplace.json"
    elif ! grep -q '"flow"' "$marketplace_file" 2>/dev/null; then
        log_warn "Existing marketplace.json found — add Flow entry manually"
        echo "         File: $marketplace_file"
    else
        log_info "Flow already in marketplace.json"
    fi

    echo ""
    log_success "Codex CLI installation complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# OpenCode Installation (local plugin)
# ─────────────────────────────────────────────────────────────────────────────

install_opencode() {
    echo ""
    echo -e "${CYAN}Installing Flow for OpenCode...${NC}"
    echo ""

    # Step 1: Clean up ALL legacy installations
    cleanup_opencode_legacy

    # Step 2: Install plugin at ~/.config/opencode/plugins/flow/
    local plugin_dir="$OPENCODE_DIR/plugins/flow"

    # Backup existing plugin if present
    if [[ -d "$plugin_dir" ]]; then
        backup_dir "$plugin_dir"
        rm -rf "$plugin_dir"
    fi

    # Create plugin directory and copy plugin files
    mkdir -p "$plugin_dir"
    cp "$PROJECT_ROOT/.opencode/plugins/flow.js" "$plugin_dir/"
    cp "$PROJECT_ROOT/package.json" "$plugin_dir/"
    cp "$PROJECT_ROOT/AGENTS.md" "$plugin_dir/"
    log_success "Installed: plugin files"

    # Copy skills
    if [[ -d "$SKILLS_DIR" ]]; then
        cp -r "$SKILLS_DIR" "$plugin_dir/skills"
        log_success "Installed: skills ($(ls -1d "$SKILLS_DIR"/*/ 2>/dev/null | wc -l) skills)"
    fi

    # Copy commands (Codex/Gemini .toml format)
    mkdir -p "$plugin_dir/commands"
    cp -r "$COMMANDS_DIR/flow" "$plugin_dir/commands/"
    log_success "Installed: commands"

    # Step 3: Update opencode.json config
    local config_file="$OPENCODE_DIR/opencode.json"

    if [[ -f "$config_file" ]]; then
        if grep -q '"flow"' "$config_file" 2>/dev/null; then
            log_info "OpenCode config already references Flow"
        else
            log_warn "Add Flow to your opencode.json plugin array:"
            echo '         "plugin": ["flow"]'
            echo "         File: $config_file"
        fi
    else
        cat > "$config_file" << 'OC_CONFIG_EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["flow"]
}
OC_CONFIG_EOF
        log_success "Created: opencode.json with Flow plugin"
    fi

    echo ""
    log_success "OpenCode installation complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# Gemini CLI Installation (extension)
# ─────────────────────────────────────────────────────────────────────────────

install_gemini() {
    echo ""
    echo -e "${CYAN}Installing Flow for Gemini CLI...${NC}"
    echo ""

    # Backup existing extension
    if [[ -d "$GEMINI_EXT_DIR" ]]; then
        backup_dir "$GEMINI_EXT_DIR"
        rm -rf "$GEMINI_EXT_DIR"
    fi

    # Create extension directory
    mkdir -p "$GEMINI_EXT_DIR"

    # Install extension manifest and context
    cp "$PROJECT_ROOT/gemini-extension.json" "$GEMINI_EXT_DIR/"
    cp "$PROJECT_ROOT/AGENTS.md" "$GEMINI_EXT_DIR/"
    log_success "Installed: extension manifest and context"

    # Install commands (Gemini uses commands/flow/*.toml)
    mkdir -p "$GEMINI_EXT_DIR/commands"
    cp -r "$COMMANDS_DIR/flow" "$GEMINI_EXT_DIR/commands/"
    log_success "Installed: commands"

    # Install skills
    if [[ -d "$SKILLS_DIR" ]]; then
        mkdir -p "$GEMINI_EXT_DIR/skills"
        cp -r "$SKILLS_DIR"/* "$GEMINI_EXT_DIR/skills/"
        log_success "Installed: skills"
    fi

    # Install hooks
    if [[ -d "$PROJECT_ROOT/hooks" ]]; then
        mkdir -p "$GEMINI_EXT_DIR/hooks"
        cp -r "$PROJECT_ROOT/hooks"/* "$GEMINI_EXT_DIR/hooks/"
        chmod +x "$GEMINI_EXT_DIR/hooks/session-start" "$GEMINI_EXT_DIR/hooks/run-hook.cmd" 2>/dev/null || true
        log_success "Installed: hooks"
    fi

    echo ""
    log_success "Gemini CLI installation complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# Google Antigravity Installation (skill directory)
# ─────────────────────────────────────────────────────────────────────────────

install_antigravity() {
    echo ""
    echo -e "${CYAN}Installing Flow for Google Antigravity...${NC}"
    echo ""

    local target_agy_dir="$ANTIGRAVITY_DIR"
    if [[ -d "$HOME/.jetski" ]]; then
        target_agy_dir="$JETSKI_DIR"
    elif [[ -d "$HOME/.gemini/jetski" ]]; then
        target_agy_dir="$GEMINI_JETSKI_DIR"
    fi

    # Backup existing
    if [[ -d "$target_agy_dir" ]]; then
        backup_dir "$target_agy_dir"
    fi

    # Create skills directory
    mkdir -p "$target_agy_dir"

    # Install skills
    if [[ -d "$SKILLS_DIR" ]]; then
        for skill_dir in "$SKILLS_DIR"/*/; do
            [[ -d "$skill_dir" ]] || continue
            local skill_name="$(basename "$skill_dir")"
            local skill_dst_dir="$target_agy_dir/$skill_name"

            # Clean and copy
            rm -rf "$skill_dst_dir"
            cp -r "$skill_dir" "$skill_dst_dir"
        done
        log_success "Installed: skills ($(ls -1d "$SKILLS_DIR"/*/ 2>/dev/null | wc -l) skills)"
    fi

    echo ""
    log_success "Google Antigravity installation complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# Beads Installation Check
# ─────────────────────────────────────────────────────────────────────────────

check_beads() {
    echo ""
    echo -e "${CYAN}Checking Beads CLI...${NC}"
    echo ""

    if command -v br &> /dev/null; then
        local version=$(br --version 2>/dev/null || echo "unknown")
        log_success "Beads CLI (br) installed: $version"
    else
        log_warn "Beads CLI not found"
        echo ""
        echo "Flow requires Beads for cross-session memory."
        echo "Install with: curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash"
        echo ""
        read -p "Install Beads now? [Y/n] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
            curl -fsSL https://raw.githubusercontent.com/Dicklesworthstone/beads_rust/main/install.sh | bash
            log_success "Beads CLI installed"
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Argument Parsing
# ─────────────────────────────────────────────────────────────────────────────

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force|--overwrite)
                FORCE_OVERWRITE=true
                shift
                ;;
            --help|-h)
                echo "Usage: install.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --force    Overwrite existing plugin installations without prompting"
                echo "  --help     Show this help message"
                echo ""
                echo "Installs Flow as a plugin for all detected AI CLI tools."
                echo "Legacy installations are automatically cleaned up."
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
    # Parse command line arguments
    parse_args "$@"

    # Show banner after parsing args
    show_banner

    # Create flow data directory
    mkdir -p "$FLOW_DATA_DIR"

    # Detect CLIs
    detect_clis

    # If none detected, ask which to install for
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
        # Ask which detected CLIs to install for
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
            a|A) ;; # Install all
            *)
                # Parse selection
                INSTALL_CLAUDE=false
                INSTALL_CODEX=false
                INSTALL_OPENCODE=false
                INSTALL_GEMINI=false
                INSTALL_ANTIGRAVITY=false
                for sel in $SELECTION; do
                    case $sel in
                        1) INSTALL_CLAUDE=true ;;
                        2) INSTALL_CODEX=true ;;
                        3) INSTALL_OPENCODE=true ;;
                        4) INSTALL_GEMINI=true ;;
                        5) INSTALL_ANTIGRAVITY=true ;;
                    esac
                done
                $INSTALL_CLAUDE || CLAUDE_INSTALLED=false
                $INSTALL_CODEX || CODEX_INSTALLED=false
                $INSTALL_OPENCODE || OPENCODE_INSTALLED=false
                $INSTALL_GEMINI || GEMINI_INSTALLED=false
                $INSTALL_ANTIGRAVITY || ANTIGRAVITY_INSTALLED=false
                ;;
        esac
    fi

    # Install for selected CLIs
    $CLAUDE_INSTALLED && install_claude
    $CODEX_INSTALLED && install_codex
    $OPENCODE_INSTALLED && install_opencode
    $GEMINI_INSTALLED && install_gemini
    $ANTIGRAVITY_INSTALLED && install_antigravity

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
    $GEMINI_INSTALLED && echo "     Gemini CLI:  /flow:setup"
    $ANTIGRAVITY_INSTALLED && echo "     Google Antigravity: flow-setup (skill)"
    echo ""
    echo "  3. Create your first flow:"
    $CLAUDE_INSTALLED && echo "     Claude Code: /flow-prd \"your feature description\""
    $CODEX_INSTALLED && echo "     Codex CLI:   /flow:prd \"your feature description\""
    $OPENCODE_INSTALLED && echo "     OpenCode:    /flow:prd \"your feature description\""
    $GEMINI_INSTALLED && echo "     Gemini CLI:  /flow:prd \"your feature description\""
    $ANTIGRAVITY_INSTALLED && echo "     Google Antigravity: flow-prd \"your feature description\""
    echo ""
    echo "Documentation: https://github.com/cofin/flow"
    echo ""
}

# Run
main "$@"
