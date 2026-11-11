#!/usr/bin/env sh
# Portable POSIX sh + awk PreToolUse safety guard for Flow.
# Enforces Git tag non-mutation, prompts on force-push/hard-reset, and guards read-only agents.
set -eu

HARNESS="claude"

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
      shift 2
      ;;
    --project=*)
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
    printf "%s|%s|%s\n", tool_name, agent_id, cmd_line
  }
')"

TOOL_NAME="${PARSED%%|*}"
REST_ONE="${PARSED#*|}"
AGENT_ID="${REST_ONE%%|*}"
CMD_LINE="${REST_ONE#*|}"

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
