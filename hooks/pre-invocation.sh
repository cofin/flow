#!/usr/bin/env sh
# Portable POSIX sh + awk PreInvocation refresh hook for Flow Studio.
# Emits {} unless an active spec.md/feedback changed on disk or a Turn-0 /plan or /learn handoff is detected.
set -eu

HOOK_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || dirname -- "$0")"
. "$HOOK_DIR/lib/common.sh"

flow_parse_args "agy" "$@"
flow_read_stdin

if [ -n "$STDIN_PAYLOAD" ] && printf '%s\n' "$STDIN_PAYLOAD" | awk '
  { buf = buf " " $0 }
  END {
    if (match(buf, /"invocationNum"[[:space:]]*:[[:space:]]*[0-9]+/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"invocationNum"[[:space:]]*:[[:space:]]*/, "", s)
      if ((s + 0) > 0) exit 0
    }
    exit 1
  }
'; then
  printf '{}\n'
  exit 0
fi

flow_resolve_project_dir

if [ ! -d "$PROJECT_DIR/.agents" ] && [ ! -L "$PROJECT_DIR/.agents" ]; then
  printf '{}\n'
  exit 0
fi

flow_resolve_worktree_context
flow_detect_worker_invocation
if [ "$IS_WORKER_AGENT" = "1" ]; then
  printf '{}\n'
  exit 0
fi

flow_runtime_paths
mkdir -p "$RUNTIME_WS_DIR" 2>/dev/null || true

DIGEST_ACC=""
if [ -d "$EFFECTIVE_ROOT/$BUNDLE_REL/specs" ]; then
  for spec_file in "$EFFECTIVE_ROOT/$BUNDLE_REL/specs"/*/spec.md "$EFFECTIVE_ROOT/$BUNDLE_REL/specs"/*/feedback/*.json; do
    [ -f "$spec_file" ] || continue
    ck_val="$(cksum "$spec_file" | awk '{ printf "%s:%s", $1, $2 }')"
    DIGEST_ACC="${DIGEST_ACC}${spec_file}=${ck_val};"
  done
fi
if [ -f "$EFFECTIVE_ROOT/.agents/studio-comments.json" ]; then
  ck_comments="$(cksum "$EFFECTIVE_ROOT/.agents/studio-comments.json" | awk '{ printf "%s:%s", $1, $2 }')"
  DIGEST_ACC="${DIGEST_ACC}comments=${ck_comments};"
fi

PREV_DIGEST=""
ACTIVE_TURN="false"
PREV_CONV=""
PREV_ROLE="coordinator"
PREV_FLOW=""
PREV_CHAPTER=""
PREV_TASKS="[]"
PREV_ACTIVITY=""
PREV_TOOL=""
PREV_FILE=""

if [ -f "$READ_STATE_FILE" ]; then
  STATE_PARSED="$(awk '
    { buf = buf " " $0 }
    END {
      pd = ""; at = "false"; cv = ""; rl = "coordinator"; fl = ""; ch = ""; ts = "[]"; act = ""; lt = ""; lf = ""
      if (match(buf, /"specDigest"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"specDigest"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); pd = s
      }
      if (match(buf, /"activeTurn"[[:space:]]*:[[:space:]]*true/)) { at = "true" }
      if (match(buf, /"conversationId"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"conversationId"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); cv = s
      }
      if (match(buf, /"role"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"role"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); rl = s
      }
      if (match(buf, /"flowId"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"flowId"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); fl = s
      }
      if (match(buf, /"chapterId"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"chapterId"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); ch = s
      }
      if (match(buf, /"taskIds"[[:space:]]*:[[:space:]]*\[[^\]]*\]/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"taskIds"[[:space:]]*:[[:space:]]*/, "", s); ts = s
      }
      if (match(buf, /"activity"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"activity"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); act = s
      }
      if (match(buf, /"lastTool"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"lastTool"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); lt = s
      }
      if (match(buf, /"lastFilePath"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"lastFilePath"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); lf = s
      }
      printf "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n", pd, at, cv, rl, fl, ch, ts, act, lt, lf
    }
  ' "$READ_STATE_FILE")"
  PREV_DIGEST="${STATE_PARSED%%|*}"; R1="${STATE_PARSED#*|}"
  ACTIVE_TURN="${R1%%|*}"; R2="${R1#*|}"
  PREV_CONV="${R2%%|*}"; R3="${R2#*|}"
  PREV_ROLE="${R3%%|*}"; R4="${R3#*|}"
  PREV_FLOW="${R4%%|*}"; R5="${R4#*|}"
  PREV_CHAPTER="${R5%%|*}"; R6="${R5#*|}"
  PREV_TASKS="${R6%%|*}"; R7="${R6#*|}"
  PREV_ACTIVITY="${R7%%|*}"; R8="${R7#*|}"
  PREV_TOOL="${R8%%|*}"; PREV_FILE="${R8#*|}"
fi

S_CONV=""
LAST_USER_TEXT=""
if [ -n "$STDIN_PAYLOAD" ]; then
  S_CONV="$(flow_extract_payload_field "$STDIN_PAYLOAD" "conversationId")"
  [ -n "$S_CONV" ] || S_CONV="$(flow_extract_payload_field "$STDIN_PAYLOAD" "session_id")"
  [ -n "$S_CONV" ] && PREV_CONV="$S_CONV"
  LAST_USER_TEXT="$(flow_extract_payload_field "$STDIN_PAYLOAD" "lastUserInput")"
  if [ -z "$LAST_USER_TEXT" ]; then
    TRANSCRIPT_P="$(flow_extract_payload_field "$STDIN_PAYLOAD" "transcriptPath")"
    if [ -n "$TRANSCRIPT_P" ] && [ -f "$TRANSCRIPT_P" ]; then
      LAST_USER_TEXT="$(awk '
        /"type"[[:space:]]*:[[:space:]]*"USER_INPUT"/ { last = $0 }
        END { print last }
      ' "$TRANSCRIPT_P" 2>/dev/null || true)"
    fi
  fi
fi

TURN0_NOTICE=""
if ! flow_sibling_plugin_present && [ -n "$LAST_USER_TEXT" ]; then
  case "$LAST_USER_TEXT" in
    *"/plan"*|*"/Plan"*)
      TURN0_NOTICE="Flow Turn-0 handoff: Keep plans outside the repository tree during /plan so Review remains active. Include concrete file path:line hints; after approval run node sidecars/studio/flow-cli.mjs spec import --from PLAN_PATH to create task worksheets."
      ;;
    *"/learn"*)
      TURN0_NOTICE="Flow Turn-0 handoff: Route durable repository conventions to .agents/bundles/knowledge/ and keep user personal preferences outside repository files."
      ;;
  esac
fi

FINAL_DIGEST=""
if [ -n "$DIGEST_ACC" ]; then
  FINAL_DIGEST="$(printf '%s' "$DIGEST_ACC" | cksum | awk '{ printf "%s-%s", $1, $2 }')"
fi

WORKTREE_NORM="$(printf '%s' "$PROJECT_DIR" | tr '\\' '/' | sed 's:/*$::')"
NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")"

write_state_digest() {
  FLOW_JSON="null"
  [ -n "$PREV_FLOW" ] && FLOW_JSON="\"$(flow_json_escape "$PREV_FLOW")\""
  CH_JSON="null"
  [ -n "$PREV_CHAPTER" ] && CH_JSON="\"$(flow_json_escape "$PREV_CHAPTER")\""
  cat > "$STATE_FILE" <<EOF
{
  "v": 1,
  "updatedAt": "$NOW_ISO",
  "harness": "$(flow_json_escape "$HARNESS")",
  "conversationId": "$(flow_json_escape "$PREV_CONV")",
  "role": "$(flow_json_escape "${PREV_ROLE:-coordinator}")",
  "flowId": $FLOW_JSON,
  "chapterId": $CH_JSON,
  "taskIds": ${PREV_TASKS:-[]},
  "worktree": "$(flow_json_escape "$WORKTREE_NORM")",
  "activity": "$(flow_json_escape "$PREV_ACTIVITY")",
  "activeTurn": $ACTIVE_TURN,
  "lastTool": "$(flow_json_escape "$PREV_TOOL")",
  "lastFilePath": "$(flow_json_escape "$PREV_FILE")",
  "specDigest": "$(flow_json_escape "$FINAL_DIGEST")"
}
EOF
}

DIGEST_NOTICE=""
if [ -n "$FINAL_DIGEST" ]; then
  if [ -z "$PREV_DIGEST" ]; then
    write_state_digest
  elif [ "$PREV_DIGEST" != "$FINAL_DIGEST" ] && [ "$ACTIVE_TURN" != "true" ]; then
    write_state_digest
    DIGEST_NOTICE="Flow Studio notice: Active spec.md or Studio review feedback changed on disk since the previous turn. Re-read the active spec.md and feedback files before mutating code."
  elif [ "$PREV_DIGEST" != "$FINAL_DIGEST" ]; then
    write_state_digest
  fi
fi

COMBINED_NOTICE="$DIGEST_NOTICE"
if [ -n "$TURN0_NOTICE" ]; then
  if [ -n "$COMBINED_NOTICE" ]; then
    COMBINED_NOTICE="$COMBINED_NOTICE $TURN0_NOTICE"
  else
    COMBINED_NOTICE="$TURN0_NOTICE"
  fi
fi

if [ -z "$COMBINED_NOTICE" ]; then
  printf '{}\n'
  exit 0
fi

CLEAN_NOTICE="$(flow_strip_xml_tags "$COMBINED_NOTICE")"
ESCAPED_NOTICE="$(flow_json_escape "$CLEAN_NOTICE")"

case "$HARNESS" in
  agy|antigravity)
    printf '{"injectSteps":[{"systemMessage":{"systemMessage":"%s"}}]}\n' "$ESCAPED_NOTICE"
    ;;
  cursor)
    printf '{"continue":true,"additional_context":"%s"}\n' "$ESCAPED_NOTICE"
    ;;
  claude|vscode|*)
    printf '{"continue":true,"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' "$ESCAPED_NOTICE"
    ;;
esac
