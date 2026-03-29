#!/usr/bin/env bash
#
# Flow Framework - Intelligent Installer
#
# Installs Flow commands and skills for supported AI CLI tools:
# - Claude Code (~/.claude/)
# - Codex CLI (~/.codex/)
# - OpenCode (~/.config/opencode/)
# - Gemini CLI (~/.gemini/extensions/flow/)
# - Google Antigravity (~/.gemini/antigravity/skills/)
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
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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
    echo "║                       Version 0.12.0                         ║"
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

    # Google Antigravity
    local target_agy_dir="$ANTIGRAVITY_DIR"
    if [[ -d "$HOME/.jetski" ]]; then
        target_agy_dir="$JETSKI_DIR"
    elif [[ -d "$HOME/.gemini/jetski" ]]; then
        target_agy_dir="$GEMINI_JETSKI_DIR"
    fi
    
    if command -v agy &> /dev/null || command -v jetski &> /dev/null || [[ -d "$ANTIGRAVITY_DIR" ]] || [[ -d "$JETSKI_DIR" ]] || [[ -d "$GEMINI_JETSKI_DIR" ]]; then
        ANTIGRAVITY_INSTALLED=true
        log_success "Google Antigravity detected"
        [[ -d "$target_agy_dir" ]] && echo "         Existing skills: $(ls -1d "$target_agy_dir"/*/ 2>/dev/null | wc -l)"
    else
        log_info "Google Antigravity not detected"
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

            # Process each file in the skill directory recursively
            find "$skill_dir" -type f | while read -r skill_file; do
                local rel_path="${skill_file#$skill_dir}"
                local dest_file="$skill_dst_dir/$rel_path"

                # Ensure parent directory exists in destination
                mkdir -p "$(dirname "$dest_file")"

                merge_or_install_file "$skill_file" "$dest_file"
            done
        done
    fi

    # Install hooks
    local hooks_src="$PROJECT_ROOT/hooks"
    local hooks_dst="$CLAUDE_DIR/hooks"

    if [[ -d "$hooks_src" ]]; then
        mkdir -p "$hooks_dst"
        for hook_file in "hooks.json" "run-hook.cmd" "session-start"; do
            if [[ -f "$hooks_src/$hook_file" ]]; then
                merge_or_install_file "$hooks_src/$hook_file" "$hooks_dst/$hook_file"
            fi
        done
        chmod +x "$hooks_dst/session-start" "$hooks_dst/run-hook.cmd" 2>/dev/null || true
        log_success "Installed: hooks"
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

    # ── Legacy cleanup ──────────────────────────────────────────────
    local legacy_cleaned=false

    # Remove old prompts
    if ls "$CODEX_DIR/prompts/flow-"*.md &>/dev/null 2>&1; then
        rm -f "$CODEX_DIR/prompts/flow-"*.md
        log_success "Removed legacy prompts"
        legacy_cleaned=true
    fi

    # Remove old skills
    for old_skill in "flow" "beads"; do
        if [[ -d "$CODEX_DIR/skills/$old_skill" ]]; then
            rm -rf "$CODEX_DIR/skills/$old_skill"
            log_success "Removed legacy skill: $old_skill"
            legacy_cleaned=true
        fi
    done

    # Remove Flow section from old AGENTS.md
    if [[ -f "$CODEX_DIR/AGENTS.md" ]] && grep -q "Flow Framework" "$CODEX_DIR/AGENTS.md" 2>/dev/null; then
        backup_file "$CODEX_DIR/AGENTS.md"
        sed -i '/^# Flow Framework/,$d' "$CODEX_DIR/AGENTS.md"
        sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$CODEX_DIR/AGENTS.md"
        log_success "Removed legacy Flow section from AGENTS.md"
        legacy_cleaned=true
    fi

    if $legacy_cleaned; then
        echo ""
        log_info "Legacy Codex installation cleaned up"
        echo ""
    fi

    # ── New plugin installation ─────────────────────────────────────
    local plugin_dir="$HOME/.codex/plugins/flow"

    # Backup existing plugin if present
    backup_dir "$plugin_dir"

    # Create plugin directory
    mkdir -p "$plugin_dir"

    # Copy plugin manifest
    mkdir -p "$plugin_dir/.codex-plugin"
    cp "$PROJECT_ROOT/.codex-plugin/plugin.json" "$plugin_dir/.codex-plugin/"
    cp "$PROJECT_ROOT/.codex-plugin/marketplace.json" "$plugin_dir/.codex-plugin/"
    log_success "Installed: plugin manifest"

    # Copy AGENTS.md context
    cp "$PROJECT_ROOT/AGENTS.md" "$plugin_dir/"
    log_success "Installed: AGENTS.md"

    # Copy commands
    mkdir -p "$plugin_dir/commands"
    cp -r "$PROJECT_ROOT/commands/flow" "$plugin_dir/commands/"
    log_success "Installed: commands"

    # Copy hooks
    mkdir -p "$plugin_dir/hooks"
    cp "$PROJECT_ROOT/hooks/hooks-codex.json" "$plugin_dir/hooks/"
    cp "$PROJECT_ROOT/hooks/run-hook.cmd" "$plugin_dir/hooks/"
    cp "$PROJECT_ROOT/hooks/session-start" "$plugin_dir/hooks/"
    chmod +x "$plugin_dir/hooks/session-start" "$plugin_dir/hooks/run-hook.cmd"
    log_success "Installed: hooks"

    # Copy skills (all of them)
    if [[ -d "$SKILLS_DIR" ]]; then
        cp -r "$SKILLS_DIR" "$plugin_dir/skills"
        log_success "Installed: skills ($(ls -1d "$SKILLS_DIR"/*/ 2>/dev/null | wc -l) skills)"
    fi

    # Create or merge marketplace.json
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
      "source": { "source": "local", "path": "~/.codex/plugins/flow" },
      "policy": { "installation": "AVAILABLE" },
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
# OpenCode Installation
# ─────────────────────────────────────────────────────────────────────────────

install_opencode() {
    echo ""
    echo -e "${CYAN}Installing Flow for OpenCode...${NC}"
    echo ""

    # ── Legacy cleanup ──────────────────────────────────────────────
    local legacy_cleaned=false

    # Remove old agent files
    if [[ -f "$OPENCODE_DIR/agents/flow.md" ]]; then
        rm -f "$OPENCODE_DIR/agents/flow.md"
        log_success "Removed legacy agents/flow.md"
        legacy_cleaned=true
    fi

    # Remove old command files
    if ls "$OPENCODE_DIR/commands/flow-"*.md &>/dev/null 2>&1; then
        rm -f "$OPENCODE_DIR/commands/flow-"*.md
        log_success "Removed legacy command files"
        legacy_cleaned=true
    fi

    if $legacy_cleaned; then
        echo ""
        log_info "Legacy OpenCode installation cleaned up"
        echo ""
    fi

    # ── Plugin installation ─────────────────────────────────────────
    local plugin_dir="$OPENCODE_DIR/plugins/flow"

    # Backup existing plugin if present
    backup_dir "$plugin_dir"

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

    # Copy commands
    mkdir -p "$plugin_dir/commands"
    cp -r "$PROJECT_ROOT/commands/flow" "$plugin_dir/commands/"
    log_success "Installed: commands"

    # Update opencode.json config
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
    cp "$SCRIPT_DIR/AGENTS.md" "$GEMINI_EXT_DIR/"
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

    # Install hooks
    if [[ -d "$SCRIPT_DIR/hooks" ]]; then
        mkdir -p "$GEMINI_EXT_DIR/hooks"
        cp -r "$SCRIPT_DIR/hooks"/* "$GEMINI_EXT_DIR/hooks/"
        chmod +x "$GEMINI_EXT_DIR/hooks/session-start" "$GEMINI_EXT_DIR/hooks/run-hook.cmd" 2>/dev/null || true
        log_success "Installed: Hooks"
    fi

    echo ""
    log_success "Gemini CLI installation complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# Google Antigravity Installation
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

    # Create skills directory
    mkdir -p "$target_agy_dir"

    # Backup existing
    backup_dir "$target_agy_dir"

    # Install skills
    local skills_src="$SKILLS_DIR"

    if [[ -d "$skills_src" ]]; then
        for skill_dir in "$skills_src"/*/; do
            [[ -d "$skill_dir" ]] || continue
            local skill_name="$(basename "$skill_dir")"
            local skill_dst_dir="$target_agy_dir/$skill_name"

            mkdir -p "$skill_dst_dir"

            find "$skill_dir" -type f | while read -r skill_file; do
                local rel_path="${skill_file#$skill_dir}"
                local dest_file="$skill_dst_dir/$rel_path"

                mkdir -p "$(dirname "$dest_file")"

                merge_or_install_file "$skill_file" "$dest_file"
            done
            log_success "Installed skill: $skill_name"
        done
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
    if ! $CLAUDE_INSTALLED && ! $CODEX_INSTALLED && ! $OPENCODE_INSTALLED && ! $GEMINI_INSTALLED && ! $ANTIGRAVITY_INSTALLED; then
        echo "No supported CLIs detected. Which would you like to install for?"
        echo ""
        echo "  1) Claude Code (~/.claude/)"
        echo "  2) Codex CLI (~/.codex/)"
        echo "  3) OpenCode (~/.config/opencode/)"
        echo "  4) Gemini CLI (~/.gemini/)"
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
    echo "Documentation: https://github.com/cofin/flow"
    echo ""
}

# Run
main "$@"
