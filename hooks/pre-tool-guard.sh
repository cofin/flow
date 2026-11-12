#!/usr/bin/env sh
# Portable POSIX sh + awk PreToolUse safety guard for Flow.
# Enforces Git tag non-mutation, prompts on force-push/hard-reset, and guards read-only agents.
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

if [ "$HARNESS" = "claude" ] && [ -n "${CURSOR_VERSION:-}" ]; then
  printf '{}\n'
  exit 0
fi

STDIN_PAYLOAD=""
if [ ! -t 0 ]; then
  STDIN_PAYLOAD="$(cat || true)"
fi

PARSED="$(printf '%s\n' "$STDIN_PAYLOAD" | awk '
  { buf = buf " " $0 }
  END {
    tool_name = ""
    cmd_line = ""
    agent_id = ""
    proj = ""
    target_path = ""

    if (match(buf, /"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
      sub(/"$/, "", s); gsub(/\\\\/, "/", s); proj = s
    } else if (match(buf, /"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
      sub(/"$/, "", s); gsub(/\\\\/, "/", s); proj = s
    } else if (match(buf, /"cwd"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"cwd"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s); gsub(/\\\\/, "/", s); proj = s
    } else if (match(buf, /"workspaceRoot"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"workspaceRoot"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s); gsub(/\\\\/, "/", s); proj = s
    }

    if (match(buf, /"toolCall"[[:space:]]*:[[:space:]]*\{[[:space:]]*"name"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"name"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      tool_name = s
    } else if (match(buf, /"tool_name"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"tool_name"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      tool_name = s
    }

    if (match(buf, /"CommandLine"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"CommandLine"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      cmd_line = s
    } else if (match(buf, /"command"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"command"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      cmd_line = s
    }

    if (match(buf, /"Path"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"Path"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); target_path = s
    } else if (match(buf, /"file_path"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"file_path"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); target_path = s
    } else if (match(buf, /"TargetFile"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"TargetFile"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); target_path = s
    }

    if (match(buf, /"agentName"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"agentName"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      agent_id = s
    } else if (match(buf, /"agent_type"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"agent_type"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      agent_id = s
    } else if (match(buf, /"subagent_type"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"subagent_type"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      agent_id = s
    }

    gsub(/\|/, " ", tool_name)
    gsub(/\|/, " ", agent_id)
    gsub(/\|/, " ", proj)
    gsub(/\|/, " ", target_path)
    printf "%s|%s|%s|%s|%s\n", tool_name, agent_id, proj, target_path, cmd_line
  }
')"

TOOL_NAME="${PARSED%%|*}"; R_1="${PARSED#*|}"
AGENT_ID="${R_1%%|*}"; R_2="${R_1#*|}"
DETECTED_PROJ="${R_2%%|*}"; R_3="${R_2#*|}"
TARGET_PATH="${R_3%%|*}"; CMD_LINE="${R_3#*|}"

if [ -z "$PROJECT_DIR" ]; then
  if [ -n "$DETECTED_PROJ" ]; then
    PROJECT_DIR="$DETECTED_PROJ"
  elif [ -n "${CURSOR_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CURSOR_PROJECT_DIR"
  elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CLAUDE_PROJECT_DIR"
  else
    PROJECT_DIR="$(pwd)"
  fi
fi

is_incomplete_flow_spec() {
  fid="$1"
  [ -n "$fid" ] || return 1
  spec_root="$PROJECT_DIR/.agents/bundles/specs/$fid"
  if [ ! -f "$spec_root/spec.md" ] && [ -f "$PROJECT_DIR/.git" ] && command -v git >/dev/null 2>&1; then
    gcom="$(git -C "$PROJECT_DIR" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
    if [ -n "$gcom" ]; then
      cmain="$(CDPATH= cd -- "$gcom/.." 2>/dev/null && pwd || true)"
      if [ -n "$cmain" ] && [ -f "$cmain/.agents/bundles/specs/$fid/spec.md" ]; then
        spec_root="$cmain/.agents/bundles/specs/$fid"
      fi
    fi
  fi
  [ -f "$spec_root/spec.md" ] || return 1

  R_META="$(awk '
    NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
    in_fm && /^---[[:space:]]*$/ { exit }
    in_fm && /^state:[[:space:]]*/ { v = $0; sub(/^state:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); st = v }
    in_fm && /^last_reviewed_commit:[[:space:]]*/ { v = $0; sub(/^last_reviewed_commit:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); lrc = v }
    END { printf "%s|%s\n", st, lrc }
  ' "$spec_root/spec.md")"
  rst="${R_META%%|*}"
  rlrc="${R_META#*|}"
  if [ "$rst" != "completed" ] || [ -z "$rlrc" ] || [ "$rlrc" = "null" ]; then
    return 0
  fi
  if [ -d "$spec_root/chapters" ]; then
    for chd in "$spec_root/chapters"/ch*; do
      [ -d "$chd" ] || continue
      [ -f "$chd/spec.md" ] || return 0
      cst="$(awk '
        NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
        in_fm && /^---[[:space:]]*$/ { exit }
        in_fm && /^state:[[:space:]]*/ { v = $0; sub(/^state:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); print v; exit }
      ' "$chd/spec.md")"
      case "$cst" in
        completed|deferred|skipped) ;;
        *) return 0 ;;
      esac
    done
  fi
  for tkf in "$spec_root"/tasks/*.md "$spec_root"/chapters/ch*/tasks/*.md; do
    [ -f "$tkf" ] || continue
    [ "$(basename "$tkf")" = "index.md" ] && continue
    tst="$(awk '
      NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
      in_fm && /^---[[:space:]]*$/ { exit }
      in_fm && /^state:[[:space:]]*/ { v = $0; sub(/^state:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); print v; exit }
    ' "$tkf")"
    case "$tst" in
      completed|closed|deferred|skipped) ;;
      *) return 0 ;;
    esac
  done
  return 1
}

DECISION="allow"
REASON=""

case "$AGENT_ID" in
  code-reviewer|quality-reviewer|researcher|*:code-reviewer|*:quality-reviewer|*:researcher)
    case "$TOOL_NAME" in
      write_file|write_to_file|edit_file|replace_file_content|multi_replace_file_content|delete_file|notebook_edit|Write|Edit|MultiEdit|NotebookEdit)
        DECISION="deny"
        REASON="Flow safety guard: read-only agent '${AGENT_ID}' is forbidden from mutating repository files."
        ;;
    esac
    ;;
esac

if [ "$DECISION" = "allow" ] && [ "$TOOL_NAME" = "delete_file" ] && [ -n "$TARGET_PATH" ]; then
  DEL_FID="$(printf '%s\n' "$TARGET_PATH" | awk '
    match($0, /\.agents\/bundles\/specs\/[A-Za-z0-9_-]+(\/spec\.md|\/)?$/) {
      s = substr($0, RSTART, RLENGTH)
      sub(/^\.agents\/bundles\/specs\//, "", s)
      sub(/\/.*$/, "", s)
      print s
    }
  ')"
  if [ -n "$DEL_FID" ] && is_incomplete_flow_spec "$DEL_FID"; then
    DECISION="deny"
    REASON="Flow safety guard: cannot delete or archive specs/${DEL_FID} while chapters or tasks remain incomplete or unreviewed."
  fi
fi

if [ "$DECISION" = "allow" ] && [ -n "$CMD_LINE" ]; then
  RM_FID="$(printf '%s\n' "$CMD_LINE" | awk '
    /(^|[;&|[:space:]])(git[[:space:]]+rm|rm|rmdir|Remove-Item)([[:space:]]|$)/ {
      if (match($0, /\.agents\/bundles\/specs\/[A-Za-z0-9_-]+(\/spec\.md|\/)?([[:space:]"'\'';&|]|$)/)) {
        s = substr($0, RSTART, RLENGTH)
        sub(/^\.agents\/bundles\/specs\//, "", s)
        sub(/[^A-Za-z0-9_-].*$/, "", s)
        print s
      }
    }
  ')"
  if [ -n "$RM_FID" ] && is_incomplete_flow_spec "$RM_FID"; then
    DECISION="deny"
    REASON="Flow safety guard: cannot delete or archive specs/${RM_FID} while chapters or tasks remain incomplete or unreviewed."
  fi
fi

if [ "$DECISION" = "allow" ] && [ -n "$CMD_LINE" ]; then
  GIT_VERDICT="$(printf '%s\n' "$CMD_LINE" | awk '
    {
      c = $0
      if (match(c, /(^|[;&|[:space:]])git[[:space:]]+push([[:space:]]+[^;&|]*)?[[:space:]]+--tags([[:space:]];|&|$)/)) {
        print "deny|Flow safety guard: creating, deleting, or pushing Git tags is forbidden by Flow discipline."
        exit
      }
      if (match(c, /(^|[;&|[:space:]])git[[:space:]]+tag([[:space:]]+|$)/)) {
        tail = substr(c, RSTART)
        sub(/^[;&|[:space:]]*git[[:space:]]+tag[[:space:]]*/, "", tail)
        sub(/[;&|].*$/, "", tail)
        gsub(/[[:space:]]+$/, "", tail)
        if (tail == "" || tail ~ /^(-l|--list|--contains|--points-at|-v|--verify)([[:space:]]|$)/) {
          print "allow|"
          exit
        }
        print "deny|Flow safety guard: creating, deleting, or pushing Git tags is forbidden by Flow discipline."
        exit
      }
      if (match(c, /(^|[;&|[:space:]])git[[:space:]]+push([[:space:]]+[^;&|]*)?[[:space:]]+(-f|--force|--force-with-lease)([[:space:];&|]|$)/)) {
        print "ask|Flow safety guard: destructive Git force-push requires explicit user confirmation."
        exit
      }
      if (match(c, /(^|[;&|[:space:]])git[[:space:]]+reset[[:space:]]+--hard([[:space:];&|]|$)/)) {
        print "ask|Flow safety guard: destructive git reset --hard requires explicit user confirmation."
        exit
      }
      print "allow|"
    }
  ')"
  V_KIND="${GIT_VERDICT%%|*}"
  V_MSG="${GIT_VERDICT#*|}"
  if [ "$V_KIND" = "deny" ]; then
    DECISION="deny"
    REASON="$V_MSG"
  elif [ "$V_KIND" = "ask" ]; then
    DECISION="ask"
    REASON="$V_MSG"
  fi
fi

ESCAPED_REASON="$(printf '%s' "$REASON" | awk '
  BEGIN { ORS = "" }
  {
    gsub(/\\/, "\\\\")
    gsub(/"/, "\\\"")
    gsub(/\r/, "")
    gsub(/\t/, " ")
    printf "%s", $0
  }
')"

case "$HARNESS" in
  agy|antigravity)
    if [ "$DECISION" = "deny" ]; then
      printf '{"decision":"deny","reason":"%s"}\n' "$ESCAPED_REASON"
    elif [ "$DECISION" = "ask" ]; then
      printf '{"decision":"force_ask","reason":"%s"}\n' "$ESCAPED_REASON"
    else
      printf '{"decision":"allow"}\n'
    fi
    ;;
  cursor)
    if [ "$DECISION" = "deny" ]; then
      printf '{"permission":"deny","user_message":"%s"}\n' "$ESCAPED_REASON"
    elif [ "$DECISION" = "ask" ]; then
      printf '{"permission":"ask","user_message":"%s"}\n' "$ESCAPED_REASON"
    else
      printf '{"permission":"allow"}\n'
    fi
    ;;
  claude|vscode|*)
    if [ "$DECISION" = "deny" ]; then
      printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$ESCAPED_REASON"
    elif [ "$DECISION" = "ask" ]; then
      printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$ESCAPED_REASON"
    else
      printf '{}\n'
    fi
    ;;
esac
