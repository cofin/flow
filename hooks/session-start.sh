#!/usr/bin/env sh
# Portable POSIX sh + awk SessionStart priming hook for Flow.
# Requires zero python3, node, or jq on the host system.
set -eu

HOOK_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || dirname -- "$0")"
. "$HOOK_DIR/lib/common.sh"

flow_parse_args "claude" "$@"

# Suppress third-party Claude hook double-firing inside Cursor when native Cursor hook is active.
if [ "$HARNESS" = "claude" ] && [ -n "${CURSOR_VERSION:-}" ]; then
  printf '{"continue":true}\n'
  exit 0
fi

flow_read_stdin

IS_SUBAGENT=0
CONV_ID=""
PARENT_CONV_ID=""
if [ -n "$STDIN_PAYLOAD" ]; then
  CONV_ID="$(flow_extract_payload_field "$STDIN_PAYLOAD" "conversationId")"
  [ -n "$CONV_ID" ] || CONV_ID="$(flow_extract_payload_field "$STDIN_PAYLOAD" "session_id")"
  [ -n "$CONV_ID" ] || CONV_ID="$(flow_extract_payload_field "$STDIN_PAYLOAD" "conversation_id")"
  PARENT_CONV_ID="$(flow_extract_payload_field "$STDIN_PAYLOAD" "parentConversationId")"
  [ -n "$PARENT_CONV_ID" ] || PARENT_CONV_ID="$(flow_extract_payload_field "$STDIN_PAYLOAD" "parent_conversation_id")"
fi

flow_resolve_project_dir
flow_detect_worker_invocation
IS_SUBAGENT="$IS_WORKER_AGENT"
flow_resolve_worktree_context

WORKTREE_NOTE=""

create_worktree_link() {
  link_src="$1"
  link_dst="$2"
  if [ -e "$link_dst" ] || [ -L "$link_dst" ]; then
    return 0
  fi
  if [ ! -e "$link_src" ]; then
    return 0
  fi
  case "$(uname -s 2>/dev/null || echo "")" in
    MINGW*|MSYS*|CYGWIN*)
      if command -v cygpath >/dev/null 2>&1; then
        win_src="$(cygpath -w "$link_src")"
        win_dst="$(cygpath -w "$link_dst")"
        if [ -d "$link_src" ]; then
          MSYS_NO_PATHCONV=1 cmd.exe /c mklink /J "$win_dst" "$win_src" >/dev/null 2>&1 && return 0
        else
          MSYS_NO_PATHCONV=1 cmd.exe /c mklink /H "$win_dst" "$win_src" >/dev/null 2>&1 && return 0
        fi
      fi
      MSYS=winsymlinks:nativestrict ln -s "$link_src" "$link_dst" 2>/dev/null || true
      ;;
    *)
      ln -s "$link_src" "$link_dst" 2>/dev/null || true
      ;;
  esac
}

if [ "$IS_LINKED_WORKTREE" = "1" ] && [ -n "$MAIN_WORKTREE" ]; then
  for shared_art in .venv node_modules uv.toml .npmrc .python-version; do
    create_worktree_link "$MAIN_WORKTREE/$shared_art" "$PROJECT_DIR/$shared_art"
  done

  if [ "$IGNORE_POLICY" = "local-only" ] && [ -d "$MAIN_WORKTREE/.agents" ]; then
    create_worktree_link "$MAIN_WORKTREE/.agents" "$PROJECT_DIR/.agents"
    if [ -w "$MAIN_WORKTREE/.agents" ]; then
      WORKTREE_NOTE="Linked Git worktree (local-only .agents): .agents is shared from primary checkout $MAIN_WORKTREE/.agents — edit Flow Markdown in $MAIN_WORKTREE/.agents (or via symlinked .agents/), and reuse symlinked .venv with uv run --no-sync (do not run make install)."
    else
      WORKTREE_NOTE="Linked Git worktree (local-only .agents): primary checkout $MAIN_WORKTREE/.agents is read-only in this sandbox; sync local .agents changes via flow worktree sync-to-main, and reuse symlinked .venv with uv run --no-sync."
    fi
  else
    WORKTREE_NOTE="Linked Git worktree (shared .agents): edit worktree .agents/ directly, and reuse symlinked .venv with uv run --no-sync (do not run make install)."
  fi
fi

record_recent_workspace() {
  ws_dir="$1"
  [ -n "$ws_dir" ] || return 0
  [ -d "$ws_dir/.agents" ] || [ -L "$ws_dir/.agents" ] || [ -e "$ws_dir/.git" ] || [ -d "$ws_dir/.jj" ] || [ -d "$ws_dir/.hg" ] || return 0
  if [ -z "${FLOW_CONFIG_DIR:-}" ]; then
    case "$ws_dir" in
      /tmp/*|/var/folders/*|*/pytest-of-*|*/Temp/*|*/sidecars/studio|*/.gemini/config/plugins/*)
        return 0
        ;;
    esac
  fi
  cfg_dir="${FLOW_CONFIG_DIR:-${XDG_CONFIG_HOME:-${HOME:-/tmp}/.config}/flow}"
  mkdir -p "$cfg_dir" 2>/dev/null || return 0
  ts_iso="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "2026-01-01T00:00:00Z")"
  printf '%s\t%s\n' "$ts_iso" "$ws_dir" >> "$cfg_dir/recent-workspaces.tsv" 2>/dev/null || true

  if [ -z "${FLOW_CONFIG_DIR:-}" ] && [ -z "${FLOW_SKIP_VSCODE_AUTO_INSTALL:-}" ]; then
    hook_dir="$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || true)"
    plugin_root="$(CDPATH= cd -- "$hook_dir/.." 2>/dev/null && pwd || true)"
    if [ -n "$plugin_root" ] && [ -f "$plugin_root/vscode-extension/install.mjs" ] && command -v node >/dev/null 2>&1; then
      needs_ext_sync=0
      for ed_dir in "${HOME:-}/.vscode" "${HOME:-}/.vscode-insiders" "${HOME:-}/.cursor" "${HOME:-}/.windsurf" "${HOME:-}/.positron"; do
        if [ -f "$ed_dir/extensions/extensions.json" ] && grep -q "cofin.flow-studio" "$ed_dir/extensions/extensions.json" 2>/dev/null; then
          needs_ext_sync=1
          break
        fi
      done
      if [ "$needs_ext_sync" -eq 1 ]; then
        node "$plugin_root/vscode-extension/install.mjs" --if-needed --update-only --quiet >/dev/null 2>&1 || true
      fi
    fi
  fi
}

flow_runtime_paths

if [ "$IS_SUBAGENT" = "1" ]; then
  lease_dir="$RUNTIME_WS_DIR/subagents"
  if mkdir -p "$lease_dir" 2>/dev/null; then
    lease_name="$(printf '%s' "$CONV_ID" | sed 's/[^A-Za-z0-9._-]/_/g')"
    [ -n "$lease_name" ] || lease_name="pid-$$"
    lease_conv="${CONV_ID:-$lease_name}"
    norm_ws="$(printf '%s' "$EFFECTIVE_ROOT" | tr '\\' '/' | sed 's:/*$::')"
    norm_wt="$(printf '%s' "$PROJECT_DIR" | tr '\\' '/' | sed 's:/*$::')"
    lease_flow_id=""
    lease_ch_id=""
    if [ -d "$EFFECTIVE_ROOT/$BUNDLE_REL/specs" ]; then
      for sf in "$EFFECTIVE_ROOT/$BUNDLE_REL/specs"/*/spec.md; do
        [ -f "$sf" ] || continue
        sf_meta="$(awk '
          NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
          in_fm && /^---[[:space:]]*$/ { exit }
          in_fm && /^flow_id:[[:space:]]*/ { v = $0; sub(/^flow_id:[[:space:]]*/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); fid = v }
          in_fm && /^state:[[:space:]]*/ { v = $0; sub(/^state:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); st = v }
          in_fm && /^current_chapter:[[:space:]]*/ { v = $0; sub(/^current_chapter:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); ch = v }
          END { if (st == "active" || st == "in_progress") printf "%s|%s\n", fid, ch }
        ' "$sf")"
        if [ -n "$sf_meta" ]; then
          lease_flow_id="${sf_meta%%|*}"
          lease_ch_id="${sf_meta#*|}"
          [ -n "$lease_flow_id" ] || lease_flow_id="$(basename "$(dirname "$sf")")"
          [ "$lease_ch_id" = "null" ] && lease_ch_id=""
          break
        fi
      done
    fi
    epoch_now="$(date -u +%s 2>/dev/null || echo 0)"
    printf '%s\n{"v":1,"harness":"%s","conversation_id":"%s","parent_conversation_id":"%s","workspace":"%s","worktree":"%s","role":"flow-subagent","flow_id":"%s","chapter_id":"%s","task_ids":[]}\n' \
      "$epoch_now" \
      "$(flow_json_escape "$HARNESS")" \
      "$(flow_json_escape "$lease_conv")" \
      "$(flow_json_escape "$PARENT_CONV_ID")" \
      "$(flow_json_escape "$norm_ws")" \
      "$(flow_json_escape "$norm_wt")" \
      "$(flow_json_escape "$lease_flow_id")" \
      "$(flow_json_escape "$lease_ch_id")" \
      > "$lease_dir/$lease_name.lease" 2>/dev/null || true
  fi
  if [ -d "$EFFECTIVE_ROOT/.agents" ]; then
    BASE_MSG="Flow subagent context: bundle root $EFFECTIVE_ROOT/$BUNDLE_REL. Stay strictly within your assigned Bounded Read Manifest."
  else
    BASE_MSG="Flow subagent context: no .agents bundle in workspace."
  fi
else
  record_recent_workspace "$PROJECT_DIR"
  ACTIVE_SPECS=""
  PENDING_SYNC=""
  DEGRADED_PLANS=""
  SPECS_SCAN_DIR="$EFFECTIVE_ROOT/$BUNDLE_REL/specs"
  if [ -d "$SPECS_SCAN_DIR" ]; then
    for spec_file in "$SPECS_SCAN_DIR"/*/spec.md; do
      [ -f "$spec_file" ] || continue
      flow_dir="$(dirname "$spec_file")"
      flow_dir_name="$(basename "$flow_dir")"
      SPEC_META="$(awk '
        NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
        in_fm && /^---[[:space:]]*$/ { exit }
        in_fm && /^flow_id:[[:space:]]*/ {
          val = $0; sub(/^flow_id:[[:space:]]*/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); gsub(/[[:space:]]+$/, "", val); flow_id = val
        }
        in_fm && /^state:[[:space:]]*/ {
          val = $0; sub(/^state:[[:space:]]*/, "", val); sub(/[[:space:]]+#.*$/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); gsub(/[[:space:]]+$/, "", val); state = val
        }
        in_fm && /^current_chapter:[[:space:]]*/ {
          val = $0; sub(/^current_chapter:[[:space:]]*/, "", val); sub(/[[:space:]]+#.*$/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); gsub(/[[:space:]]+$/, "", val); chapter = val
        }
        in_fm && /^current_task:[[:space:]]*/ {
          val = $0; sub(/^current_task:[[:space:]]*/, "", val); sub(/[[:space:]]+#.*$/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); gsub(/[[:space:]]+$/, "", val); task = val
        }
        in_fm && /^planning_quality:[[:space:]]*/ {
          val = $0; sub(/^planning_quality:[[:space:]]*/, "", val); sub(/[[:space:]]+#.*$/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); gsub(/[[:space:]]+$/, "", val); pq = val
        }
        END { printf "%s|%s|%s|%s|%s\n", flow_id, state, chapter, task, pq }
      ' "$spec_file")"

      s_fid="${SPEC_META%%|*}"; s_rest1="${SPEC_META#*|}"
      s_state="${s_rest1%%|*}"; s_rest2="${s_rest1#*|}"
      s_ch="${s_rest2%%|*}"; s_rest3="${s_rest2#*|}"
      s_task="${s_rest3%%|*}"; s_pq="${s_rest3#*|}"
      [ -z "$s_fid" ] && s_fid="$flow_dir_name"

      if [ -d "$flow_dir/chapters" ]; then
        for ch_dir in "$flow_dir/chapters"/ch*; do
          [ -d "$ch_dir" ] || continue
          ch_spec="$ch_dir/spec.md"
          [ -f "$ch_spec" ] || continue
          ch_id="$(basename "$ch_dir")"
          CH_META="$(awk '
            NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
            in_fm && /^---[[:space:]]*$/ { exit }
            in_fm && /^state:[[:space:]]*/ {
              val = $0; sub(/^state:[[:space:]]*/, "", val); sub(/[[:space:]]+#.*$/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); gsub(/[[:space:]]+$/, "", val); st = val
            }
            in_fm && /^last_reviewed_commit:[[:space:]]*/ {
              val = $0; sub(/^last_reviewed_commit:[[:space:]]*/, "", val); sub(/[[:space:]]+#.*$/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); gsub(/[[:space:]]+$/, "", val); lrc = val
            }
            in_fm && /^planning_quality:[[:space:]]*/ {
              val = $0; sub(/^planning_quality:[[:space:]]*/, "", val); sub(/[[:space:]]+#.*$/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); gsub(/[[:space:]]+$/, "", val); cpq = val
            }
            END { printf "%s|%s|%s\n", st, lrc, cpq }
          ' "$ch_spec")"
          c_st="${CH_META%%|*}"; c_rest="${CH_META#*|}"
          c_lrc="${c_rest%%|*}"; c_pq="${c_rest#*|}"
          [ "$c_pq" = "degraded" ] && s_pq="degraded"
          if { [ -z "$s_ch" ] || [ "$s_ch" = "null" ]; } && [ "$c_st" != "completed" ] && [ "$c_st" != "deferred" ] && [ "$c_st" != "skipped" ]; then
            s_ch="$ch_id"
          fi
          if [ -d "$ch_dir/tasks" ]; then
            set -- "$ch_dir/tasks"/*.md
            if [ -f "$1" ]; then
              TASK_COUNTS="$(awk '
                FNR == 1 {
                  fname = FILENAME
                  sub(/^.*\//, "", fname)
                  skip_file = (fname == "index.md") ? 1 : 0
                  in_fm = 0
                  if (!skip_file) tot++
                }
                skip_file { next }
                FNR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
                in_fm && /^---[[:space:]]*$/ { in_fm = 0; next }
                in_fm && /^state:[[:space:]]*/ {
                  val = $0; sub(/^state:[[:space:]]*/, "", val); sub(/[[:space:]]+#.*$/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); gsub(/[[:space:]]+$/, "", val)
                  if (val == "completed" || val == "closed" || val == "deferred" || val == "skipped") done++
                  in_fm = 0
                }
                END { printf "%d|%d\n", tot + 0, done + 0 }
              ' "$@")"
              t_tot="${TASK_COUNTS%%|*}"
              t_done="${TASK_COUNTS#*|}"
              if [ "$c_st" != "paused" ]; then
                if { [ "$t_tot" -gt 0 ] && [ "$t_done" -eq "$t_tot" ] && [ "$c_st" != "completed" ] && [ "$c_st" != "deferred" ] && [ "$c_st" != "skipped" ]; } || { [ "$c_st" = "completed" ] && { [ -z "$c_lrc" ] || [ "$c_lrc" = "null" ]; }; }; then
                  if [ -n "$PENDING_SYNC" ]; then
                    PENDING_SYNC="$PENDING_SYNC, $s_fid/$ch_id"
                  else
                    PENDING_SYNC="$s_fid/$ch_id"
                  fi
                fi
              fi
            fi
          fi
        done
      fi

      SPEC_INFO=""
      if [ -n "$s_fid" ] && [ "$s_state" != "completed" ] && [ "$s_state" != "archived" ]; then
        has_ch=0
        has_tk=0
        [ -n "$s_ch" ] && [ "$s_ch" != "null" ] && has_ch=1
        [ -n "$s_task" ] && [ "$s_task" != "null" ] && has_tk=1
        if [ "$has_ch" = "1" ] && [ "$has_tk" = "1" ]; then
          SPEC_INFO="${s_fid}(${s_state}, chapter=${s_ch}, task=${s_task})"
        elif [ "$has_ch" = "1" ]; then
          SPEC_INFO="${s_fid}(${s_state}, chapter=${s_ch})"
        elif [ "$has_tk" = "1" ]; then
          SPEC_INFO="${s_fid}(${s_state}, task=${s_task})"
        else
          SPEC_INFO="${s_fid}(${s_state})"
        fi
        if [ "$s_pq" = "degraded" ]; then
          if [ -n "$DEGRADED_PLANS" ]; then
            DEGRADED_PLANS="$DEGRADED_PLANS, $s_fid"
          else
            DEGRADED_PLANS="$s_fid"
          fi
        fi
      fi

      if [ -n "$SPEC_INFO" ]; then
        if [ -n "$ACTIVE_SPECS" ]; then
          ACTIVE_SPECS="$ACTIVE_SPECS, $SPEC_INFO"
        else
          ACTIVE_SPECS="$SPEC_INFO"
        fi
      fi
    done
  fi

  if [ -d "$EFFECTIVE_ROOT/.agents" ]; then
    BASE_MSG="Flow Spec-Driven Development is active. Resolve the bundle root from .agents/setup-state.json (default .agents/bundles/), read its index.md and applicable nested knowledge chapters, and follow skills/flow/references/state.md for direct Markdown + Git continuity."
    BASE_MSG="$BASE_MSG Workspace bundle root: $BUNDLE_REL."
    if [ -n "$WORKTREE_NOTE" ]; then
      BASE_MSG="$BASE_MSG $WORKTREE_NOTE"
    fi
    if [ -f "$EFFECTIVE_ROOT/.agents/skills/index.md" ]; then
      BASE_MSG="$BASE_MSG Project-local domain and review skills index: .agents/skills/index.md."
    fi
    if [ -n "$ACTIVE_SPECS" ]; then
      BASE_MSG="$BASE_MSG Active specs: $ACTIVE_SPECS."
    fi
    if [ -n "$DEGRADED_PLANS" ]; then
      BASE_MSG="$BASE_MSG Degraded planning quality warning (planning_quality=degraded — not planned with the strongest model): $DEGRADED_PLANS."
    fi
    if [ -n "$PENDING_SYNC" ]; then
      BASE_MSG="$BASE_MSG Pending chapter review/Markdown sync: $PENDING_SYNC."
    fi
    if [ "$HARNESS" = "agy" ] || [ "$HARNESS" = "antigravity" ]; then
      BASE_MSG="$BASE_MSG Flow Studio UI: call flow_studio MCP tool (or open Flow Studio in Plugins)."
    else
      BASE_MSG="$BASE_MSG Flow Studio UI: npx --yes --package github:cofin/flow flow-studio."
    fi
    if ! command -v flow >/dev/null 2>&1; then
      BASE_MSG="$BASE_MSG CLI not on PATH: run node \"$HOOK_DIR/../bin/flow.mjs\" install-cli."
    fi
  else
    BASE_MSG="Flow plugin loaded (no .agents/ bundle in this workspace; run /flow:setup to initialize)."
  fi
fi

OPENCODE_LEGACY_PLUGIN="${XDG_CONFIG_HOME:-${HOME:-}/.config}/opencode/plugins/flow.js"
if [ -f "$OPENCODE_LEGACY_PLUGIN" ] && grep -q -e 'flow-rule-adapter:start' -e 'export default async' "$OPENCODE_LEGACY_PLUGIN" 2>/dev/null; then
  BASE_MSG="$BASE_MSG Stale pre-0.26 OpenCode Flow plugin at $OPENCODE_LEGACY_PLUGIN: OpenCode V2 rejects it; delete it and run: opencode plugin add github:cofin/flow."
fi

BASE_MSG="$(flow_strip_xml_tags "$BASE_MSG")"
ESCAPED_MSG="$(flow_json_escape "$BASE_MSG")"

case "$HARNESS" in
  agy|antigravity)
    printf '{"injectSteps":[{"systemMessage":{"systemMessage":"%s"}}]}\n' "$ESCAPED_MSG"
    ;;
  cursor)
    printf '{"continue":true,"additional_context":"%s"}\n' "$ESCAPED_MSG"
    ;;
  json)
    printf '{"bundle_root":"%s","active_specs":"%s","message":"%s"}\n' "$BUNDLE_REL" "$ACTIVE_SPECS" "$ESCAPED_MSG"
    ;;
  claude|vscode|*)
    printf '{"continue":true,"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$ESCAPED_MSG" "$ESCAPED_MSG"
    ;;
esac
