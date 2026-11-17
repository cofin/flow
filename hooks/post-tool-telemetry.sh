#!/usr/bin/env sh
# Portable POSIX sh + awk PostToolUse live telemetry writer for Flow Studio.
# Includes stepIdx transcript fallback and ProceedMetadataGuard for artifact files.
set -eu

HOOK_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || dirname -- "$0")"
. "$HOOK_DIR/lib/common.sh"

flow_parse_args "agy" "$@"
flow_read_stdin

PARSED="$(printf '%s\n' "$STDIN_PAYLOAD" | awk '
  { buf = buf " " $0 }
  END {
    ws = ""; conv = ""; parent_conv = ""; tool_nm = ""; fpath = ""; step_idx = ""; tp = ""; art = ""

    if (match(buf, /"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); ws = s
    } else if (match(buf, /"cwd"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"cwd"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); ws = s
    }

    if (match(buf, /"conversationId"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"conversationId"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); conv = s
    } else if (match(buf, /"session_id"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"session_id"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); conv = s
    }

    if (match(buf, /"parentConversationId"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"parentConversationId"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); parent_conv = s
    }

    if (match(buf, /"toolCall"[[:space:]]*:[[:space:]]*\{[[:space:]]*"name"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"name"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); tool_nm = s
    } else if (match(buf, /"tool_name"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"tool_name"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); tool_nm = s
    }

    if (match(buf, /"Path"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"Path"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); fpath = s
    } else if (match(buf, /"file_path"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"file_path"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); fpath = s
    }

    if (match(buf, /"stepIdx"[[:space:]]*:[[:space:]]*[0-9]+/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"stepIdx"[[:space:]]*:[[:space:]]*/, "", s); step_idx = s
    }
    if (match(buf, /"transcriptPath"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"transcriptPath"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); tp = s
    }
    if (match(buf, /"artifactDirectoryPath"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"artifactDirectoryPath"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); art = s
    }

    gsub(/\|/, " ", ws); gsub(/\|/, " ", conv); gsub(/\|/, " ", parent_conv)
    gsub(/\|/, " ", tool_nm); gsub(/\|/, " ", fpath); gsub(/\|/, " ", tp); gsub(/\|/, " ", art)
    printf "%s|%s|%s|%s|%s|%s|%s|%s\n", ws, conv, parent_conv, tool_nm, fpath, step_idx, tp, art
  }
')"

P_WS="${PARSED%%|*}"; R1="${PARSED#*|}"
P_CONV="${R1%%|*}"; R2="${R1#*|}"
P_PARENT="${R2%%|*}"; R3="${R2#*|}"
P_TOOL="${R3%%|*}"; R4="${R3#*|}"
P_FILE="${R4%%|*}"; R5="${R4#*|}"
P_STEP="${R5%%|*}"; R6="${R5#*|}"
P_TRANSCRIPT="${R6%%|*}"; P_ARTIFACT_DIR="${R6#*|}"

if [ -z "$PROJECT_DIR" ]; then
  PROJECT_DIR="${P_WS:-$(pwd)}"
fi

if { [ -z "$P_TOOL" ] || [ -z "$P_FILE" ]; } && [ -n "$P_TRANSCRIPT" ] && [ -f "$P_TRANSCRIPT" ]; then
  REC="$(awk -v sidx="$P_STEP" '
    {
      if (sidx != "" && index($0, "\"step_index\":" sidx) == 0 && index($0, "\"step_index\": " sidx) == 0) next
      if (match($0, /"name"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        t = substr($0, RSTART, RLENGTH); sub(/^.*"name"[[:space:]]*:[[:space:]]*"/, "", t); sub(/"$/, "", t)
      }
      if (match($0, /"Path"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        f = substr($0, RSTART, RLENGTH); sub(/^.*"Path"[[:space:]]*:[[:space:]]*"/, "", f); sub(/"$/, "", f); gsub(/\\\\/, "/", f)
      }
    }
    END { printf "%s|%s\n", t, f }
  ' "$P_TRANSCRIPT" 2>/dev/null || echo "|")"
  [ -z "$P_TOOL" ] && P_TOOL="${REC%%|*}"
  [ -z "$P_FILE" ] && P_FILE="${REC#*|}"
fi

if [ ! -d "$PROJECT_DIR/.agents" ] && [ ! -L "$PROJECT_DIR/.agents" ]; then
  printf '{}\n'
  exit 0
fi

flow_resolve_worktree_context
flow_runtime_paths
mkdir -p "$RUNTIME_WS_DIR" 2>/dev/null || true

PREV_DIGEST=""; PREV_ROLE=""; PREV_FLOW=""; PREV_CHAPTER=""; PREV_TASKS="[]"
if [ -f "$READ_STATE_FILE" ]; then
  PREV_META="$(awk '
    { buf = buf " " $0 }
    END {
      pd = ""; rl = ""; fl = ""; ch = ""; ts = "[]"
      if (match(buf, /"specDigest"[[:space:]]*:[[:space:]]*"[^"]*"/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"specDigest"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); pd = s }
      if (match(buf, /"role"[[:space:]]*:[[:space:]]*"[^"]*"/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"role"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); rl = s }
      if (match(buf, /"flowId"[[:space:]]*:[[:space:]]*"[^"]*"/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"flowId"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); fl = s }
      if (match(buf, /"chapterId"[[:space:]]*:[[:space:]]*"[^"]*"/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"chapterId"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); ch = s }
      if (match(buf, /"taskIds"[[:space:]]*:[[:space:]]*\[[^\]]*\]/)) { s = substr(buf, RSTART, RLENGTH); sub(/^.*"taskIds"[[:space:]]*:[[:space:]]*/, "", s); ts = s }
      printf "%s|%s|%s|%s|%s\n", pd, rl, fl, ch, ts
    }
  ' "$READ_STATE_FILE")"
  PREV_DIGEST="${PREV_META%%|*}"; RM1="${PREV_META#*|}"
  PREV_ROLE="${RM1%%|*}"; RM2="${RM1#*|}"
  PREV_FLOW="${RM2%%|*}"; RM3="${RM2#*|}"
  PREV_CHAPTER="${RM3%%|*}"; PREV_TASKS="${RM3#*|}"
fi

ROLE="${PREV_ROLE:-coordinator}"
if [ -n "$P_PARENT" ]; then
  ROLE="flow-subagent"
fi

FLOW_ID="$PREV_FLOW"
CHAPTER_ID="$PREV_CHAPTER"
TASK_IDS_JSON="${PREV_TASKS:-[]}"

if [ -n "$P_FILE" ]; then
  PATH_META="$(printf '%s\n' "$P_FILE" | awk '
    {
      p = $0; fl = ""; ch = ""; tk = ""
      if (match(p, /\/specs\/[^\/]+/)) { s = substr(p, RSTART, RLENGTH); sub(/^\/specs\//, "", s); fl = s }
      if (match(p, /\/chapters\/[^\/]+/)) { s = substr(p, RSTART, RLENGTH); sub(/^\/chapters\//, "", s); ch = s }
      if (match(p, /\/tasks\/[^\/]+\.md$/)) {
        s = substr(p, RSTART, RLENGTH); sub(/^\/tasks\//, "", s); sub(/\.md$/, "", s)
        if (s != "index") { sub(/-.*$/, "", s); tk = s }
      }
      printf "%s|%s|%s\n", fl, ch, tk
    }
  ')"
  PF_FLOW="${PATH_META%%|*}"; PFR="${PATH_META#*|}"
  PF_CH="${PFR%%|*}"; PF_TASK="${PFR#*|}"
  [ -n "$PF_FLOW" ] && FLOW_ID="$PF_FLOW"
  [ -n "$PF_CH" ] && CHAPTER_ID="$PF_CH"
  if [ -n "$PF_TASK" ]; then
    TASK_IDS_JSON="[\"$PF_TASK\"]"
  fi
fi

if [ -z "$FLOW_ID" ] && [ -d "$EFFECTIVE_ROOT/$BUNDLE_REL/specs" ]; then
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
      FLOW_ID="${sf_meta%%|*}"
      [ -n "$FLOW_ID" ] || FLOW_ID="$(basename "$(dirname "$sf")")"
      if [ -z "$CHAPTER_ID" ]; then
        CAND_CH="${sf_meta#*|}"
        [ "$CAND_CH" != "null" ] && CHAPTER_ID="$CAND_CH"
      fi
      break
    fi
  done
fi

PROCEED_GUARD=""
if [ -n "$P_ARTIFACT_DIR" ] && [ -n "$P_FILE" ]; then
  case "$P_FILE" in
    "$P_ARTIFACT_DIR"/implementation_plan.md|"$P_ARTIFACT_DIR"/learning_proposal.md)
      if [ ! -f "${P_FILE}.metadata.json" ]; then
        PROCEED_GUARD="missing_artifact_metadata"
      fi
      ;;
  esac
fi

ACTIVITY=""
if [ -n "$P_TOOL" ] && [ -n "$P_FILE" ]; then
  ACTIVITY="$P_TOOL $P_FILE"
elif [ -n "$P_TOOL" ]; then
  ACTIVITY="Running $P_TOOL"
fi

WORKTREE_NORM="$(printf '%s' "$PROJECT_DIR" | tr '\\' '/' | sed 's:/*$::')"
NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")"

FLOW_JSON="null"
[ -n "$FLOW_ID" ] && FLOW_JSON="\"$(flow_json_escape "$FLOW_ID")\""
CH_JSON="null"
[ -n "$CHAPTER_ID" ] && CH_JSON="\"$(flow_json_escape "$CHAPTER_ID")\""

cat > "$STATE_FILE" <<EOF
{
  "v": 1,
  "updatedAt": "$NOW_ISO",
  "harness": "$(flow_json_escape "$HARNESS")",
  "conversationId": "$(flow_json_escape "$P_CONV")",
  "role": "$(flow_json_escape "$ROLE")",
  "flowId": $FLOW_JSON,
  "chapterId": $CH_JSON,
  "taskIds": $TASK_IDS_JSON,
  "worktree": "$(flow_json_escape "$WORKTREE_NORM")",
  "activity": "$(flow_json_escape "$ACTIVITY")",
  "activeTurn": true,
  "lastTool": "$(flow_json_escape "$P_TOOL")",
  "lastFilePath": "$(flow_json_escape "$P_FILE")",
  "proceedGuard": "$(flow_json_escape "$PROCEED_GUARD")",
  "specDigest": "$(flow_json_escape "$PREV_DIGEST")"
}
EOF

printf '{}\n'
