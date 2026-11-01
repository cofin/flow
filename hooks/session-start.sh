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
if [ -d "$PROJECT_DIR/$BUNDLE_REL/specs" ]; then
  for spec_file in "$PROJECT_DIR/$BUNDLE_REL/specs"/*/spec.md; do
    if [ -f "$spec_file" ]; then
      SPEC_INFO="$(awk '
        NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
        in_fm && /^---[[:space:]]*$/ { exit }
        in_fm && /^flow_id:[[:space:]]*/ {
          val = $0; sub(/^flow_id:[[:space:]]*/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); flow_id = val
        }
        in_fm && /^state:[[:space:]]*/ {
          val = $0; sub(/^state:[[:space:]]*/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); state = val
        }
        in_fm && /^current_task:[[:space:]]*/ {
          val = $0; sub(/^current_task:[[:space:]]*/, "", val); gsub(/^["'\'']|["'\'']$/, "", val); task = val
        }
        END {
          if (flow_id != "" && state != "completed" && state != "archived") {
            if (task != "" && task != "null") {
              printf "%s(%s, task=%s)", flow_id, state, task
            } else {
              printf "%s(%s)", flow_id, state
            }
          }
        }
      ' "$spec_file")"
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
