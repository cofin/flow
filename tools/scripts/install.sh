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
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$PROJECT_ROOT"
TEMPLATES_DIR="$PROJECT_ROOT/templates"
SKILLS_DIR="$PROJECT_ROOT/skills"
FLOW_DATA_DIR="$HOME/.flow"
BACKUP_DIR="$FLOW_DATA_DIR/backups/$(date +%Y%m%d-%H%M%S)"
MERGE_HISTORY="$FLOW_DATA_DIR/merge-history.json"

# Flags (parsed from command line)
USE_LLM_MERGE=false
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
    echo "║           Flow Framework - Intelligent Installer             ║"
    echo "║                       Version 0.5.0                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    # Show merge mode if enabled
    if $USE_LLM_MERGE; then
        echo -e "${GREEN}Mode: LLM-Assisted Merge${NC} (using Claude/Gemini for intelligent merging)"
        echo ""
    elif $FORCE_OVERWRITE; then
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
# LLM-Assisted Merge Functions
# ─────────────────────────────────────────────────────────────────────────────

# Detect available LLM CLI
detect_llm_cli() {
    if command -v claude &> /dev/null; then
        echo "claude"
    elif command -v gemini &> /dev/null; then
        echo "gemini"
    else
        echo ""
    fi
}

# Merge files using LLM
# Returns 0 on success, 1 on failure/skip
merge_with_llm() {
    local source_file="$1"
    local dest_file="$2"
    local output_file="$3"
    local llm_cli="$4"

    local source_content
    local dest_content
    source_content=$(cat "$source_file")
    dest_content=$(cat "$dest_file")

    local merge_prompt="Merge these two skill files. The SOURCE is the new version from Flow.
The DESTINATION is the user's existing version with potential customizations.

Rules:
1. Keep user customizations that don't conflict with new features
2. Update any outdated command syntax or patterns
3. Preserve user-added sections or examples
4. Use the new structure/format from SOURCE where applicable
5. Output ONLY the merged content, no explanations

--- SOURCE (new version) ---
$source_content

--- DESTINATION (user's version) ---
$dest_content

Output the merged content:"

    local merged
    case "$llm_cli" in
        claude)
            merged=$(echo "$merge_prompt" | claude -p 2>/dev/null) || return 1
            ;;
        gemini)
            merged=$(gemini -p "$merge_prompt" 2>/dev/null) || return 1
            ;;
        *)
            return 1
            ;;
    esac

    # Validate we got content
    if [[ -z "$merged" || ${#merged} -lt 50 ]]; then
        return 1
    fi

    echo "$merged" > "$output_file"
    return 0
}

# Show diff and prompt for action
show_diff_prompt() {
    local source_file="$1"
    local dest_file="$2"
    local name="$3"

    echo ""
    echo -e "${YELLOW}Differences found in: $name${NC}"
    echo "─────────────────────────────────────────"

    # Show compact diff
    diff --color=auto -u "$dest_file" "$source_file" | head -50 || true

    local line_count
    line_count=$(diff "$dest_file" "$source_file" | wc -l)
    if [[ $line_count -gt 50 ]]; then
        echo "... ($((line_count - 50)) more lines)"
    fi

    echo "─────────────────────────────────────────"
    echo ""
    echo "Options:"
    echo "  o) Overwrite with new version"
    echo "  k) Keep existing version"
    echo "  v) View full diff"
    echo ""
    read -p "Select [o/k/v]: " -n 1 -r
    echo

    case $REPLY in
        o|O)
            return 0  # Overwrite
            ;;
        v|V)
            diff --color=auto -u "$dest_file" "$source_file" | less
            show_diff_prompt "$source_file" "$dest_file" "$name"
            return $?
            ;;
        *)
            return 1  # Keep existing
            ;;
    esac
}

# Intelligent merge for a single file
# Handles LLM merge, diff preview, or simple overwrite based on flags
merge_or_install_file() {
    local source_file="$1"
    local dest_file="$2"
    local name="$(basename "$source_file")"
    local llm_cli

    # If destination doesn't exist, simple copy
    if [[ ! -f "$dest_file" ]]; then
        cp "$source_file" "$dest_file"
        log_success "Installed: $name"
        return 0
    fi

    # Check if files are identical
    if diff -q "$source_file" "$dest_file" &>/dev/null; then
        log_info "Unchanged: $name"
        return 0
    fi

    # Force overwrite mode
    if $FORCE_OVERWRITE; then
        cp "$source_file" "$dest_file"
        log_success "Overwrote: $name"
        return 0
    fi

    # LLM merge mode
    if $USE_LLM_MERGE; then
        llm_cli=$(detect_llm_cli)
        if [[ -n "$llm_cli" ]]; then
            log_info "Merging $name with $llm_cli..."
            local temp_merged
            temp_merged=$(mktemp)

            if merge_with_llm "$source_file" "$dest_file" "$temp_merged" "$llm_cli"; then
                # Show what the LLM produced
                echo ""
                echo -e "${CYAN}LLM Merge Preview for: $name${NC}"
                echo "─────────────────────────────────────────"
                diff --color=auto -u "$dest_file" "$temp_merged" | head -30 || true
                echo "─────────────────────────────────────────"
                echo ""
                read -p "Accept merge? [Y/n/d(iff)]: " -n 1 -r
                echo

                case $REPLY in
                    n|N)
                        rm "$temp_merged"
                        log_info "Skipped: $name (kept existing)"
                        return 0
                        ;;
                    d|D)
                        diff --color=auto -u "$dest_file" "$temp_merged" | less
                        read -p "Accept merge after review? [Y/n]: " -n 1 -r
                        echo
                        if [[ $REPLY =~ ^[Nn]$ ]]; then
                            rm "$temp_merged"
                            log_info "Skipped: $name (kept existing)"
                            return 0
                        fi
                        ;;
                esac

                cp "$temp_merged" "$dest_file"
                rm "$temp_merged"
                log_success "Merged: $name (with $llm_cli)"

                # Record merge history
                record_merge_history "$name" "$llm_cli"
                return 0
            else
                log_warn "LLM merge failed for $name, falling back to diff"
                rm -f "$temp_merged"
            fi
        else
            log_warn "No LLM CLI available, falling back to diff"
        fi
    fi

    # Default: show diff and prompt
    if show_diff_prompt "$source_file" "$dest_file" "$name"; then
        cp "$source_file" "$dest_file"
        log_success "Updated: $name"
    else
        log_info "Kept existing: $name"
    fi

    return 0
}

# Record merge in history file
record_merge_history() {
    local file_name="$1"
    local llm_used="$2"
    local timestamp
    timestamp=$(date -Iseconds)

    mkdir -p "$(dirname "$MERGE_HISTORY")"

    # Create or append to merge history
    if [[ ! -f "$MERGE_HISTORY" ]]; then
        echo '{"merges":[]}' > "$MERGE_HISTORY"
    fi

    # Append entry (simple JSON append - jq would be cleaner but may not be installed)
    local temp_file
    temp_file=$(mktemp)
    if command -v jq &>/dev/null; then
        jq --arg f "$file_name" --arg l "$llm_used" --arg t "$timestamp" \
            '.merges += [{"file": $f, "llm": $l, "timestamp": $t}]' \
            "$MERGE_HISTORY" > "$temp_file" && mv "$temp_file" "$MERGE_HISTORY"
    else
        # Fallback: just log to file
        echo "$timestamp: Merged $file_name using $llm_used" >> "${MERGE_HISTORY%.json}.log"
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

    # Gemini CLI
    if command -v gemini &> /dev/null || [[ -d "$GEMINI_DIR" ]]; then
        GEMINI_INSTALLED=true
        log_success "Gemini CLI detected"
        [[ -d "$GEMINI_EXT_DIR" ]] && echo "         Existing extension: Found"
    else
        log_info "Gemini CLI not detected"
    fi

    # Google Antigravity (Jetski)
    local target_agy_dir="$ANTIGRAVITY_DIR"
    if [[ -d "$HOME/.jetski" ]]; then
        target_agy_dir="$JETSKI_DIR"
    elif [[ -d "$HOME/.gemini/jetski" ]]; then
        target_agy_dir="$GEMINI_JETSKI_DIR"
    fi
    
    if command -v agy &> /dev/null || command -v jetski &> /dev/null || [[ -d "$ANTIGRAVITY_DIR" ]] || [[ -d "$JETSKI_DIR" ]] || [[ -d "$GEMINI_JETSKI_DIR" ]]; then
        ANTIGRAVITY_INSTALLED=true
        log_success "Google Antigravity (Jetski) detected"
        [[ -d "$target_agy_dir" ]] && echo "         Existing skills: $(ls -1d "$target_agy_dir"/*/ 2>/dev/null | wc -l)"
    else
        log_info "Google Antigravity (Jetski) not detected"
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

    # Install skills (merge with existing using intelligent merge)
    local skills_src="$SKILLS_DIR"
    local skills_dst="$CLAUDE_DIR/skills"

    if [[ -d "$skills_src" ]]; then
        for skill_dir in "$skills_src"/*/; do
            local skill_name="$(basename "$skill_dir")"
            local skill_dst_dir="$skills_dst/$skill_name"

            mkdir -p "$skill_dst_dir"

            # Process each file in the skill directory
            for skill_file in "$skill_dir"*; do
                [[ -f "$skill_file" ]] || continue
                local file_name="$(basename "$skill_file")"
                local dest_file="$skill_dst_dir/$file_name"

                merge_or_install_file "$skill_file" "$dest_file"
            done
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

    # Install skills (beads and flow only for now) with intelligent merge
    local skills_src="$SKILLS_DIR"
    local skills_dst="$CODEX_DIR/skills"

    for skill_name in "flow" "beads"; do
        local skill_dir="$skills_src/$skill_name"
        if [[ -d "$skill_dir" ]]; then
            local skill_dst_dir="$skills_dst/$skill_name"
            mkdir -p "$skill_dst_dir"

            # Process each file in the skill directory
            for skill_file in "$skill_dir"/*; do
                [[ -f "$skill_file" ]] || continue
                local file_name="$(basename "$skill_file")"
                local dest_file="$skill_dst_dir/$file_name"

                merge_or_install_file "$skill_file" "$dest_file"
            done
        fi
    done

    # Install MCP configuration for flow-think server
    local mcp_config_src="$TEMPLATES_DIR/codex/mcp-config.toml"
    local config_dst="$CODEX_DIR/config.toml"

    if [[ -f "$mcp_config_src" ]]; then
        if [[ -f "$config_dst" ]]; then
            if grep -q "mcp_servers.flow-think" "$config_dst" 2>/dev/null; then
                log_info "MCP config: flow-think already configured"
            else
                # Backup existing config
                backup_file "$config_dst"
                # Append MCP configuration
                echo "" >> "$config_dst"
                echo "# --- Flow Framework MCP Configuration ---" >> "$config_dst"
                cat "$mcp_config_src" >> "$config_dst"
                # Replace placeholder with actual install path
                sed -i "s|\${FLOW_INSTALL_PATH}|$SCRIPT_DIR|g" "$config_dst"
                log_success "MCP config: Added flow-think server to config.toml"
            fi
        else
            # Create new config with MCP settings
            cp "$mcp_config_src" "$config_dst"
            # Replace placeholder with actual install path
            sed -i "s|\${FLOW_INSTALL_PATH}|$SCRIPT_DIR|g" "$config_dst"
            log_success "MCP config: Created config.toml with flow-think server"
        fi
    fi

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
# Gemini CLI Installation
# ─────────────────────────────────────────────────────────────────────────────

install_gemini() {
    echo ""
    echo -e "${CYAN}Installing Flow for Gemini CLI...${NC}"
    echo ""

    # Create extension directory
    mkdir -p "$GEMINI_EXT_DIR"

    # Backup existing
    backup_dir "$GEMINI_EXT_DIR"

    # Install extension manifest and context
    cp "$SCRIPT_DIR/gemini-extension.json" "$GEMINI_EXT_DIR/"
    cp "$SCRIPT_DIR/GEMINI.md" "$GEMINI_EXT_DIR/"
    log_success "Installed: extension manifest and context"

    # Install commands
    mkdir -p "$GEMINI_EXT_DIR/commands"
    cp -r "$SCRIPT_DIR/commands/flow" "$GEMINI_EXT_DIR/commands/"
    log_success "Installed: Flow commands"

    # Install templates
    mkdir -p "$GEMINI_EXT_DIR/templates"
    cp -r "$TEMPLATES_DIR"/* "$GEMINI_EXT_DIR/templates/"
    log_success "Installed: Templates"

    # Install skills (all) to the extension directory
    # Gemini CLI automatically discovers and registers skills within extensions
    mkdir -p "$GEMINI_EXT_DIR/skills"
    cp -r "$SKILLS_DIR"/* "$GEMINI_EXT_DIR/skills/"
    log_success "Installed: Skills"

    # Install flow-think MCP server (standalone executable)
    local TOOLS_DIR="$SCRIPT_DIR/tools"
    if [[ -d "$TOOLS_DIR/flow-think" ]]; then
        local mcp_exe="$TOOLS_DIR/flow-think/dist/flow-think-mcp"

        # Build if executable doesn't exist
        if [[ ! -f "$mcp_exe" ]]; then
            log_info "Building flow-think MCP server..."
            (cd "$TOOLS_DIR/flow-think" && ./scripts/build.sh) || {
                log_warn "Failed to build flow-think MCP server"
                return
            }
        fi

        # Copy standalone executable
        mkdir -p "$GEMINI_EXT_DIR/tools/flow-think/dist"
        cp "$mcp_exe" "$GEMINI_EXT_DIR/tools/flow-think/dist/"
        chmod +x "$GEMINI_EXT_DIR/tools/flow-think/dist/flow-think-mcp"
        log_success "Installed: flow-think MCP server (standalone executable)"
        echo "         Tool available as: mcp__flow-think__flow_think"
    else
        log_warn "flow-think MCP server not found"
    fi

    echo ""
    log_success "Gemini CLI installation complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# Google Antigravity Installation
# ─────────────────────────────────────────────────────────────────────────────

install_antigravity() {
    echo ""
    echo -e "${CYAN}Installing Flow for Google Antigravity (Jetski)...${NC}"
    echo ""

    local target_agy_dir="$ANTIGRAVITY_DIR"
    if [[ -d "$HOME/.jetski" ]]; then
        target_agy_dir="$JETSKI_DIR"
    elif [[ -d "$HOME/.gemini/jetski" ]]; then
        target_agy_dir="$GEMINI_JETSKI_DIR"
    fi

    # Create skills directory
    mkdir -p "$target_agy_dir"

    # Backup existing
    backup_dir "$target_agy_dir"

    # Install Antigravity workflow skills
    local skills_src="$TEMPLATES_DIR/antigravity/skills"

    if [[ -d "$skills_src" ]]; then
        for skill_dir in "$skills_src"/*/; do
            [[ -d "$skill_dir" ]] || continue
            local skill_name="$(basename "$skill_dir")"
            local skill_dst_dir="$target_agy_dir/$skill_name"

            mkdir -p "$skill_dst_dir"

            for skill_file in "$skill_dir"*; do
                [[ -f "$skill_file" ]] || continue
                local file_name="$(basename "$skill_file")"
                local dest_file="$skill_dst_dir/$file_name"

                merge_or_install_file "$skill_file" "$dest_file"
            done
            log_success "Installed skill: $skill_name"
        done
    fi

    echo ""
    log_success "Google Antigravity (Jetski) installation complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# MCP Installation
# ─────────────────────────────────────────────────────────────────────────────

install_mcp() {
    echo ""
    echo -e "${CYAN}Installing Flow Think MCP Server...${NC}"
    echo ""

    local mcp_src="$SCRIPT_DIR/tools/flow-think"
    local mcp_dst="$FLOW_DATA_DIR/mcp/flow-think"
    local mcp_exe="$mcp_src/dist/flow-think-mcp"

    # Check if flow-think exists
    if [[ ! -d "$mcp_src" ]]; then
        log_warn "Flow Think MCP source not found: $mcp_src"
        log_info "Skipping MCP installation"
        return
    fi

    # Build executable if it doesn't exist
    if [[ ! -f "$mcp_exe" ]]; then
        log_info "Building Flow Think MCP..."
        if command -v bun &>/dev/null; then
            (cd "$mcp_src" && bun install && ./scripts/build.sh) || {
                log_error "Failed to build Flow Think MCP with bun"
                return
            }
        elif command -v npm &>/dev/null && command -v tsc &>/dev/null; then
            log_info "Bun not found, using npm and tsc fallback..."
            (cd "$mcp_src" && npm install && ./scripts/build.sh) || {
                log_error "Failed to build Flow Think MCP with npm"
                return
            }
            # Fallback path outputs to index.js since compile isn't available
            mcp_exe="$mcp_src/dist/index.js"
        else
            log_error "Bun or (npm+tsc) required to build Flow Think MCP"
            log_info "Install Bun: curl -fsSL https://bun.sh/install | bash"
            return
        fi
    fi

    # Create destination directory
    mkdir -p "$mcp_dst"

    # Copy the built entrypoint
    cp "$mcp_exe" "$mcp_dst/flow-think-mcp"
    chmod +x "$mcp_dst/flow-think-mcp"

    echo ""
    log_success "Flow Think MCP installed (standalone executable)"
    log_info "Path: $mcp_dst/flow-think-mcp"
}

configure_mcp_for_claude() {
    local claude_json="$HOME/.claude.json"
    local mcp_exe="$FLOW_DATA_DIR/mcp/flow-think/flow-think-mcp"

    log_info "Configuring MCP for Claude Code..."

    # Check if standalone executable exists
    if [[ ! -f "$mcp_exe" ]]; then
        log_warn "Flow Think MCP executable not found at $mcp_exe"
        log_info "Run install_mcp first"
        return
    fi

    local mcp_config='{
  "flow-think": {
    "command": "'"$mcp_exe"'",
    "args": [],
    "env": {
      "FLOW_MCP_BEADS_SYNC": "true",
      "FLOW_MCP_OUTPUT_FORMAT": "console"
    }
  }
}'

    if [[ -f "$claude_json" ]]; then
        backup_file "$claude_json"

        if command -v jq &>/dev/null; then
            local temp_file
            temp_file=$(mktemp)
            jq --argjson mcp "$mcp_config" '.mcpServers = (.mcpServers // {}) + $mcp' "$claude_json" > "$temp_file" && mv "$temp_file" "$claude_json"
            log_success "Merged: MCP configuration into ~/.claude.json"
        else
            log_warn "jq not installed - manual MCP config required"
            echo "         Add to ~/.claude.json mcpServers:"
            echo "         \"flow-think\": { \"command\": \"$mcp_exe\", \"args\": [] }"
        fi
    else
        # Create new claude.json
        if command -v jq &>/dev/null; then
            echo "{\"mcpServers\": $mcp_config}" | jq '.' > "$claude_json"
            log_success "Created: ~/.claude.json with MCP configuration"
        else
            cat > "$claude_json" << EOF
{
  "mcpServers": {
    "flow-think": {
      "command": "$mcp_exe",
      "args": [],
      "env": {
        "FLOW_MCP_BEADS_SYNC": "true"
      }
    }
  }
}
EOF
            log_success "Created: ~/.claude.json with MCP configuration"
        fi
    fi
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
# Argument Parsing
# ─────────────────────────────────────────────────────────────────────────────

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --merge-with-llm|--llm)
                USE_LLM_MERGE=true
                shift
                ;;
            --force|--overwrite)
                FORCE_OVERWRITE=true
                shift
                ;;
            --help|-h)
                echo "Usage: install.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --merge-with-llm  Use Claude/Gemini CLI to intelligently merge"
                echo "                    existing skills with new versions"
                echo "  --force           Overwrite existing files without prompting"
                echo "  --help            Show this help message"
                echo ""
                echo "Without flags, shows diff preview for conflicts."
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

    # Show banner after parsing args (so we know the mode)
    show_banner

    # Create flow data directory
    mkdir -p "$FLOW_DATA_DIR"

    # Check templates exist
    if [[ ! -d "$TEMPLATES_DIR" ]]; then
        log_error "Templates directory not found: $TEMPLATES_DIR"
        log_error "Please run this script from the Flow repository"
        exit 1
    fi

    # Detect CLIs
    detect_clis

    # If none detected, ask which to install for
    if ! $CLAUDE_INSTALLED && ! $CODEX_INSTALLED && ! $OPENCODE_INSTALLED && ! $GEMINI_INSTALLED; then
        echo "No supported CLIs detected. Which would you like to install for?"
        echo ""
        echo "  1) Claude Code (~/.claude/)"
        echo "  2) Codex CLI (~/.codex/)"
        echo "  3) OpenCode (~/.config/opencode/)"
        echo "  4) Gemini CLI (~/.gemini/)"
        echo "  5) All of the above"
        echo "  6) Exit"
        echo ""
        read -p "Select [1-6]: " -n 1 -r
        echo
        case $REPLY in
            1) CLAUDE_INSTALLED=true ;;
            2) CODEX_INSTALLED=true ;;
            3) OPENCODE_INSTALLED=true ;;
            4) GEMINI_INSTALLED=true ;;
            5) CLAUDE_INSTALLED=true; CODEX_INSTALLED=true; OPENCODE_INSTALLED=true; GEMINI_INSTALLED=true ;;
            6) exit 0 ;;
        esac
    else
        # Ask which detected CLIs to install for
        echo "Which CLIs would you like to install Flow for?"
        echo ""
        $CLAUDE_INSTALLED && echo "  1) Claude Code"
        $CODEX_INSTALLED && echo "  2) Codex CLI"
        $OPENCODE_INSTALLED && echo "  3) OpenCode"
        $GEMINI_INSTALLED && echo "  4) Gemini CLI"
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
                for sel in $SELECTION; do
                    case $sel in
                        1) INSTALL_CLAUDE=true ;;
                        2) INSTALL_CODEX=true ;;
                        3) INSTALL_OPENCODE=true ;;
                        4) INSTALL_GEMINI=true ;;
                    esac
                done
                $INSTALL_CLAUDE || CLAUDE_INSTALLED=false
                $INSTALL_CODEX || CODEX_INSTALLED=false
                $INSTALL_OPENCODE || OPENCODE_INSTALLED=false
                $INSTALL_GEMINI || GEMINI_INSTALLED=false
                ;;
        esac
    fi

    # Install for selected CLIs
    $CLAUDE_INSTALLED && install_claude
    $CODEX_INSTALLED && install_codex
    $OPENCODE_INSTALLED && install_opencode
    $GEMINI_INSTALLED && install_gemini
    $ANTIGRAVITY_INSTALLED && install_antigravity

    # Install MCP server
    install_mcp

    # Configure MCP for Claude Code
    $CLAUDE_INSTALLED && configure_mcp_for_claude

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
    fi

    if [[ -f "$MERGE_HISTORY" ]] || [[ -f "${MERGE_HISTORY%.json}.log" ]]; then
        echo "Merge history: $FLOW_DATA_DIR/"
    fi
    echo ""

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
    echo "Documentation: https://github.com/your-org/flow"
    echo ""
}

# Run
main "$@"
