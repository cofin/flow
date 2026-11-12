#!/usr/bin/env sh
# Portable POSIX sh + awk SessionStart priming hook for Flow.
# Requires zero python3, node, or jq on the host system.
set -eu

HARNESS="claude"
PROJECT_DIR=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --harness)
      HARNESS="${2:-claude}"
      shift 2
      ;;
    --harness=*)
      HARNESS="${1#*=}"
      shift 1
      ;;
    --project)
      PROJECT_DIR="${2:-}"
      shift 2
      ;;
    --project=*)
      PROJECT_DIR="${1#*=}"
      shift 1
      ;;
    *)
      shift 1
      ;;
  esac
done

# Suppress third-party Claude hook double-firing inside Cursor when native Cursor hook is active.
if [ "$HARNESS" = "claude" ] && [ -n "${CURSOR_VERSION:-}" ]; then
  printf '{"continue":true}\n'
  exit 0
fi

STDIN_PAYLOAD=""
if [ ! -t 0 ]; then
  STDIN_PAYLOAD="$(cat || true)"
fi

IS_SUBAGENT=0
if [ -n "$STDIN_PAYLOAD" ]; then
  PARSED_STDIN="$(printf '%s\n' "$STDIN_PAYLOAD" | awk '
    {
      buf = buf " " $0
    }
    END {
      subag = 0
      if (match(buf, /"parentConversationId"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        subag = 1
      }
      proj = ""
      if (match(buf, /"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        proj = s
      } else if (match(buf, /"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        proj = s
      } else if (match(buf, /"cwd"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"cwd"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        proj = s
      } else if (match(buf, /"workspaceRoot"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"workspaceRoot"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        proj = s
      }
      printf "%d|%s\n", subag, proj
    }
  ')"
  IS_SUBAGENT="${PARSED_STDIN%%|*}"
  DETECTED_PROJ="${PARSED_STDIN#*|}"
  if [ -z "$PROJECT_DIR" ] && [ -n "$DETECTED_PROJ" ]; then
    PROJECT_DIR="$DETECTED_PROJ"
  fi
fi

if [ -z "$PROJECT_DIR" ]; then
  if [ -n "${CURSOR_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CURSOR_PROJECT_DIR"
  elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CLAUDE_PROJECT_DIR"
  else
    PROJECT_DIR="$(pwd)"
  fi
fi

IS_LINKED_WORKTREE=0
MAIN_WORKTREE=""
if [ -f "$PROJECT_DIR/.git" ] && command -v git >/dev/null 2>&1; then
  GIT_COMMON="$(git -C "$PROJECT_DIR" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || git -C "$PROJECT_DIR" rev-parse --git-common-dir 2>/dev/null || true)"
  if [ -n "$GIT_COMMON" ]; then
    case "$GIT_COMMON" in
      /*) COMMON_ABS="$GIT_COMMON" ;;
      *) COMMON_ABS="$(CDPATH= cd -- "$PROJECT_DIR" && CDPATH= cd -- "$GIT_COMMON" 2>/dev/null && pwd || true)" ;;
    esac
    if [ -n "$COMMON_ABS" ]; then
      CAND_MAIN="$(CDPATH= cd -- "$COMMON_ABS/.." 2>/dev/null && pwd || true)"
      PROJ_ABS="$(CDPATH= cd -- "$PROJECT_DIR" 2>/dev/null && pwd || printf '%s' "$PROJECT_DIR")"
      if [ -n "$CAND_MAIN" ] && [ "$CAND_MAIN" != "$PROJ_ABS" ]; then
        IS_LINKED_WORKTREE=1
        MAIN_WORKTREE="$CAND_MAIN"
      fi
    fi
  fi
fi

WORKTREE_NOTE=""
EFFECTIVE_ROOT="$PROJECT_DIR"
IGNORE_POLICY=""

read_setup_field() {
  json_file="$1"
  field_name="$2"
  [ -f "$json_file" ] || return 0
  awk -v key="$field_name" '
    { buf = buf " " $0 }
    END {
      pat = "\"" key "\"[[:space:]]*:[[:space:]]*\"[^\"]+\""
      if (match(buf, pat)) {
        s = substr(buf, RSTART, RLENGTH)
        sub("^.*\"" key "\"[[:space:]]*:[[:space:]]*\"", "", s)
        sub(/"$/, "", s)
        print s
      }
    }
  ' "$json_file"
}

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
          if MSYS_NO_PATHCONV=1 cmd.exe /c mklink /J "$win_dst" "$win_src" >/dev/null 2>&1; then
            return 0
          fi
        else
          if MSYS_NO_PATHCONV=1 cmd.exe /c mklink /H "$win_dst" "$win_src" >/dev/null 2>&1; then
            return 0
          fi
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
  for shared_art in .venv node_modules uv.toml .npmrc; do
    create_worktree_link "$MAIN_WORKTREE/$shared_art" "$PROJECT_DIR/$shared_art"
  done

  IGNORE_POLICY="$(read_setup_field "$PROJECT_DIR/.agents/setup-state.json" "ignore_policy")"
  if [ -z "$IGNORE_POLICY" ]; then
    IGNORE_POLICY="$(read_setup_field "$MAIN_WORKTREE/.agents/setup-state.json" "ignore_policy")"
  fi
  if [ -z "$IGNORE_POLICY" ]; then
    if [ -d "$PROJECT_DIR/.agents" ] && [ ! -L "$PROJECT_DIR/.agents" ] && git -C "$PROJECT_DIR" ls-files --error-unmatch .agents/bundles/index.md >/dev/null 2>&1; then
      IGNORE_POLICY="shared"
    elif [ -d "$MAIN_WORKTREE/.agents" ]; then
      IGNORE_POLICY="local-only"
    else
      IGNORE_POLICY="shared"
    fi
  fi

  if [ "$IGNORE_POLICY" = "local-only" ] && [ -d "$MAIN_WORKTREE/.agents" ]; then
    create_worktree_link "$MAIN_WORKTREE/.agents" "$PROJECT_DIR/.agents"
    EFFECTIVE_ROOT="$MAIN_WORKTREE"
    if [ -w "$MAIN_WORKTREE/.agents" ]; then
      WORKTREE_NOTE="Linked Git worktree (local-only .agents): .agents is shared from primary checkout $MAIN_WORKTREE/.agents — edit Flow Markdown in $MAIN_WORKTREE/.agents (or via symlinked .agents/), and reuse symlinked .venv with uv run --no-sync (do not run make install)."
    else
      WORKTREE_NOTE="Linked Git worktree (local-only .agents): primary checkout $MAIN_WORKTREE/.agents is read-only in this sandbox; sync local .agents changes via tools/worktree_env.py --sync-to-main, and reuse symlinked .venv with uv run --no-sync."
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
        if [ -d "$ed_dir" ]; then
          if [ ! -f "$ed_dir/extensions/extensions.json" ] || ! grep -q "cofin.flow-studio" "$ed_dir/extensions/extensions.json" 2>/dev/null; then
            needs_ext_sync=1
            break
          fi
        fi
      done
      if [ "$needs_ext_sync" -eq 1 ]; then
        node "$plugin_root/vscode-extension/install.mjs" --if-needed --quiet >/dev/null 2>&1 || true
      fi
    fi
  fi
}

BUNDLE_REL=".agents/bundles"
DETECTED_ROOT="$(read_setup_field "$EFFECTIVE_ROOT/.agents/setup-state.json" "bundle_root")"
if [ -n "$DETECTED_ROOT" ]; then
  BUNDLE_REL="$DETECTED_ROOT"
fi

if [ "$IS_SUBAGENT" = "1" ]; then
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
              if { [ "$t_tot" -gt 0 ] && [ "$t_done" -eq "$t_tot" ] && [ "$c_st" != "completed" ] && [ "$c_st" != "deferred" ] && [ "$c_st" != "skipped" ]; } || { [ "$c_st" = "completed" ] && { [ -z "$c_lrc" ] || [ "$c_lrc" = "null" ]; }; }; then
                if [ -n "$PENDING_SYNC" ]; then
                  PENDING_SYNC="$PENDING_SYNC, $s_fid/$ch_id"
                else
                  PENDING_SYNC="$s_fid/$ch_id"
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
      BASE_MSG="$BASE_MSG Degraded planning quality warning (planning_quality=degraded — not planned with optimal primary frontier thinking model): $DEGRADED_PLANS."
    fi
    if [ -n "$PENDING_SYNC" ]; then
      BASE_MSG="$BASE_MSG Pending chapter review/Markdown sync: $PENDING_SYNC."
    fi
    if [ "$HARNESS" = "agy" ] || [ "$HARNESS" = "antigravity" ]; then
      BASE_MSG="$BASE_MSG Flow Studio UI: [Open Flow Studio](sidecar://flow/studio/dashboard)."
    else
      BASE_MSG="$BASE_MSG Flow Studio UI: npx --yes --package github:cofin/flow flow-studio."
    fi
  else
    BASE_MSG="Flow plugin loaded (no .agents/ bundle in this workspace; run /flow:setup to initialize)."
  fi
fi

OPENCODE_LEGACY_PLUGIN="${XDG_CONFIG_HOME:-${HOME:-}/.config}/opencode/plugins/flow.js"
if [ -f "$OPENCODE_LEGACY_PLUGIN" ] && grep -q -e 'flow-rule-adapter:start' -e 'export default async' "$OPENCODE_LEGACY_PLUGIN" 2>/dev/null; then
  BASE_MSG="$BASE_MSG Stale pre-0.26 OpenCode Flow plugin at $OPENCODE_LEGACY_PLUGIN: OpenCode V2 rejects it; delete it and run: opencode plugin add github:cofin/flow."
fi

ESCAPED_MSG="$(printf '%s' "$BASE_MSG" | awk '
  BEGIN { ORS = "" }
  {
    gsub(/\\/, "\\\\")
    gsub(/"/, "\\\"")
    gsub(/\r/, "")
    gsub(/\t/, " ")
    if (NR > 1) printf "\\n"
    printf "%s", $0
  }
')"

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
