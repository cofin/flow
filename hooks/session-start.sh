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

if [ -z "$PROJECT_DIR" ] && [ -n "$STDIN_PAYLOAD" ]; then
  PROJECT_DIR="$(printf '%s\n' "$STDIN_PAYLOAD" | awk '
    {
      buf = buf " " $0
    }
    END {
      if (match(buf, /"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        print s
        exit
      }
      if (match(buf, /"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        print s
        exit
      }
      if (match(buf, /"cwd"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"cwd"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        print s
        exit
      }
      if (match(buf, /"workspaceRoot"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"workspaceRoot"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        print s
        exit
      }
    }
  ')"
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

record_recent_workspace() {
  ws_dir="$1"
  [ -n "$ws_dir" ] || return 0
  [ -d "$ws_dir/.agents" ] || [ -e "$ws_dir/.git" ] || [ -d "$ws_dir/.jj" ] || [ -d "$ws_dir/.hg" ] || return 0
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
record_recent_workspace "$PROJECT_DIR"

BUNDLE_REL=".agents/bundles"
if [ -f "$PROJECT_DIR/.agents/setup-state.json" ]; then
  DETECTED_ROOT="$(awk '
    { buf = buf " " $0 }
    END {
      if (match(buf, /"bundle_root"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"bundle_root"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        print s
      }
    }
  ' "$PROJECT_DIR/.agents/setup-state.json")"
  if [ -n "$DETECTED_ROOT" ]; then
    BUNDLE_REL="$DETECTED_ROOT"
  fi
fi

ACTIVE_SPECS=""
PENDING_SYNC=""
if [ -d "$PROJECT_DIR/$BUNDLE_REL/specs" ]; then
  for spec_file in "$PROJECT_DIR/$BUNDLE_REL/specs"/*/spec.md; do
    if [ -f "$spec_file" ]; then
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
        END { printf "%s|%s|%s|%s\n", flow_id, state, chapter, task }
      ' "$spec_file")"

      s_fid="${SPEC_META%%|*}"; s_rest1="${SPEC_META#*|}"
      s_state="${s_rest1%%|*}"; s_rest2="${s_rest1#*|}"
      s_ch="${s_rest2%%|*}"; s_task="${s_rest2#*|}"
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
            END { printf "%s|%s\n", st, lrc }
          ' "$ch_spec")"
          c_st="${CH_META%%|*}"
          c_lrc="${CH_META#*|}"
          if { [ -z "$s_ch" ] || [ "$s_ch" = "null" ]; } && [ "$c_st" != "completed" ] && [ "$c_st" != "deferred" ] && [ "$c_st" != "skipped" ]; then
            s_ch="$ch_id"
          fi
          if [ -d "$ch_dir/tasks" ]; then
            t_tot=0
            t_done=0
            for tf in "$ch_dir/tasks"/*.md; do
              [ -f "$tf" ] || continue
              [ "$(basename "$tf")" = "index.md" ] && continue
              t_tot=$((t_tot + 1))
              tst="$(awk '
                NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
                in_fm && /^---[[:space:]]*$/ { exit }
                in_fm && /^state:[[:space:]]*/ {
                  val = $0; sub(/^state:[[:space:]]*/, "", val); sub(/[[:space:]]+#.*$/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); gsub(/[[:space:]]+$/, "", val); print val; exit
                }
              ' "$tf")"
              case "$tst" in
                completed|closed|deferred|skipped) t_done=$((t_done + 1)) ;;
              esac
            done
            if { [ "$t_tot" -gt 0 ] && [ "$t_done" -eq "$t_tot" ] && [ "$c_st" != "completed" ] && [ "$c_st" != "deferred" ] && [ "$c_st" != "skipped" ]; } || { [ "$c_st" = "completed" ] && { [ -z "$c_lrc" ] || [ "$c_lrc" = "null" ]; }; }; then
              if [ -n "$PENDING_SYNC" ]; then
                PENDING_SYNC="$PENDING_SYNC, $s_fid/$ch_id"
              else
                PENDING_SYNC="$s_fid/$ch_id"
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
      fi

      if [ -n "$SPEC_INFO" ]; then
        if [ -n "$ACTIVE_SPECS" ]; then
          ACTIVE_SPECS="$ACTIVE_SPECS, $SPEC_INFO"
        else
          ACTIVE_SPECS="$SPEC_INFO"
        fi
      fi
    fi
  done
fi

BASE_MSG="Flow Spec-Driven Development is active. Resolve the bundle root from .agents/setup-state.json (default .agents/bundles/), read its index.md and applicable nested knowledge chapters, and follow skills/flow/references/state.md for direct Markdown + Git continuity."
if [ -d "$PROJECT_DIR/.agents" ]; then
  BASE_MSG="$BASE_MSG Workspace bundle root: $BUNDLE_REL."
  if [ -f "$PROJECT_DIR/.agents/skills/index.md" ]; then
    BASE_MSG="$BASE_MSG Project-local domain and review skills index: .agents/skills/index.md."
  fi
  if [ -n "$ACTIVE_SPECS" ]; then
    BASE_MSG="$BASE_MSG Active specs: $ACTIVE_SPECS."
  fi
  if [ -n "$PENDING_SYNC" ]; then
    BASE_MSG="$BASE_MSG Pending chapter review/Markdown sync: $PENDING_SYNC."
  fi
  if [ "$HARNESS" = "agy" ] || [ "$HARNESS" = "antigravity" ]; then
    BASE_MSG="$BASE_MSG Flow Studio UI: [Open Flow Studio](sidecar://flow/studio/dashboard)."
  else
    BASE_MSG="$BASE_MSG Flow Studio UI: npx flow-studio."
  fi
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
