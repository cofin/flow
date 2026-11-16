#!/usr/bin/env sh
# Portable POSIX sh + awk PostInvocation hook for Flow Studio.
# Clears activeTurn in runtime studio-live-state.json when an invocation concludes.
set -eu

HOOK_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || dirname -- "$0")"
. "$HOOK_DIR/lib/common.sh"

flow_parse_args "agy" "$@"
flow_read_stdin
flow_resolve_project_dir

P_CONV="$(flow_extract_payload_field "$STDIN_PAYLOAD" "conversationId")"
flow_resolve_worktree_context
flow_runtime_paths

if [ ! -f "$READ_STATE_FILE" ]; then
  printf '{}\n'
  exit 0
fi

mkdir -p "$RUNTIME_WS_DIR" 2>/dev/null || true

PREV_META="$(awk '
  { buf = buf " " $0 }
  END {
    pd = ""; lt = ""; lf = ""; rl = "coordinator"; fl = ""; ch = ""; ts = "[]"; act = ""
    if (match(buf, /"specDigest"[[:space:]]*:[[:space:]]*"[^"]*"/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"specDigest"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); pd = s }
    if (match(buf, /"lastTool"[[:space:]]*:[[:space:]]*"[^"]*"/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"lastTool"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); lt = s }
    if (match(buf, /"lastFilePath"[[:space:]]*:[[:space:]]*"[^"]*"/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"lastFilePath"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); lf = s }
    if (match(buf, /"role"[[:space:]]*:[[:space:]]*"[^"]*"/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"role"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); rl = s }
    if (match(buf, /"flowId"[[:space:]]*:[[:space:]]*"[^"]*"/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"flowId"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); fl = s }
    if (match(buf, /"chapterId"[[:space:]]*:[[:space:]]*"[^"]*"/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"chapterId"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); ch = s }
    if (match(buf, /"taskIds"[[:space:]]*:[[:space:]]*\[[^\]]*\]/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"taskIds"[[:space:]]*:[[:space:]]*/, "", s); ts = s }
    if (match(buf, /"activity"[[:space:]]*:[[:space:]]*"[^"]*"/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"activity"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); act = s }
    printf "%s|%s|%s|%s|%s|%s|%s|%s\n", pd, lt, lf, rl, fl, ch, ts, act
  }
' "$READ_STATE_FILE")"

PREV_DIGEST="${PREV_META%%|*}"; RM1="${PREV_META#*|}"
PREV_TOOL="${RM1%%|*}"; RM2="${RM1#*|}"
PREV_FILE="${RM2%%|*}"; RM3="${RM2#*|}"
PREV_ROLE="${RM3%%|*}"; RM4="${RM3#*|}"
PREV_FLOW="${RM4%%|*}"; RM5="${RM4#*|}"
PREV_CHAPTER="${RM5%%|*}"; RM6="${RM5#*|}"
PREV_TASKS="${RM6%%|*}"; PREV_ACTIVITY="${RM6#*|}"

WORKTREE_NORM="$(printf '%s' "$PROJECT_DIR" | tr '\\' '/' | sed 's:/*$::')"
NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")"
FLOW_JSON="null"
[ -n "$PREV_FLOW" ] && FLOW_JSON="\"$(flow_json_escape "$PREV_FLOW")\""
CH_JSON="null"
[ -n "$PREV_CHAPTER" ] && CH_JSON="\"$(flow_json_escape "$PREV_CHAPTER")\""

cat > "$STATE_FILE" <<EOF
{
  "v": 1,
  "updatedAt": "$NOW_ISO",
  "harness": "$(flow_json_escape "$HARNESS")",
  "conversationId": "$(flow_json_escape "$P_CONV")",
  "role": "$(flow_json_escape "${PREV_ROLE:-coordinator}")",
  "flowId": $FLOW_JSON,
  "chapterId": $CH_JSON,
  "taskIds": ${PREV_TASKS:-[]},
  "worktree": "$(flow_json_escape "$WORKTREE_NORM")",
  "activity": "$(flow_json_escape "$PREV_ACTIVITY")",
  "activeTurn": false,
  "lastTool": "$(flow_json_escape "$PREV_TOOL")",
  "lastFilePath": "$(flow_json_escape "$PREV_FILE")",
  "specDigest": "$(flow_json_escape "$PREV_DIGEST")"
}
EOF

printf '{}\n'
