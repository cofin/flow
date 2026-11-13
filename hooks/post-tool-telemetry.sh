#!/usr/bin/env sh
# Portable POSIX sh + awk PostToolUse live telemetry writer for Flow Studio.
# Updates ${FLOW_RUNTIME_DIR:-$TMPDIR/flow-runtime}/<ws_id>/studio-live-state.json only when .agents/ exists.
set -eu

HARNESS="agy"
PROJECT_DIR=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --harness)
      HARNESS="${2:-agy}"
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

STDIN_PAYLOAD=""
if [ ! -t 0 ]; then
  STDIN_PAYLOAD="$(cat || true)"
fi

PARSED="$(printf '%s\n' "$STDIN_PAYLOAD" | awk '
  { buf = buf " " $0 }
  END {
    ws = ""
    conv = ""
    parent_conv = ""
    tool_nm = ""
    fpath = ""

    if (match(buf, /"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      gsub(/\\\\/, "/", s)
      ws = s
    } else if (match(buf, /"cwd"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"cwd"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      gsub(/\\\\/, "/", s)
      ws = s
    }

    if (match(buf, /"conversationId"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"conversationId"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      conv = s
    } else if (match(buf, /"session_id"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"session_id"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      conv = s
    } else if (match(buf, /"conversation_id"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"conversation_id"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      conv = s
    }

    if (match(buf, /"parentConversationId"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"parentConversationId"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      parent_conv = s
    } else if (match(buf, /"parent_conversation_id"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"parent_conversation_id"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      parent_conv = s
    }

    if (match(buf, /"toolCall"[[:space:]]*:[[:space:]]*\{[[:space:]]*"name"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"name"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      tool_nm = s
    } else if (match(buf, /"tool_name"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"tool_name"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      tool_nm = s
    }

    if (match(buf, /"Path"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"Path"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      gsub(/\\\\/, "/", s)
      fpath = s
    } else if (match(buf, /"file_path"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"file_path"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      gsub(/\\\\/, "/", s)
      fpath = s
    }

    gsub(/\|/, " ", ws)
    gsub(/\|/, " ", conv)
    gsub(/\|/, " ", parent_conv)
    gsub(/\|/, " ", tool_nm)
    gsub(/\|/, " ", fpath)
    printf "%s|%s|%s|%s|%s\n", ws, conv, parent_conv, tool_nm, fpath
  }
')"

P_WS="${PARSED%%|*}"; R1="${PARSED#*|}"
P_CONV="${R1%%|*}"; R2="${R1#*|}"
P_PARENT="${R2%%|*}"; R3="${R2#*|}"
P_TOOL="${R3%%|*}"; P_FILE="${R3#*|}"

if [ -z "$PROJECT_DIR" ]; then
  PROJECT_DIR="${P_WS:-$(pwd)}"
fi

if [ ! -d "$PROJECT_DIR/.agents" ] && [ ! -L "$PROJECT_DIR/.agents" ]; then
  printf '{}\n'
  exit 0
fi

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

EFFECTIVE_ROOT="$PROJECT_DIR"
if [ -f "$PROJECT_DIR/.git" ] && command -v git >/dev/null 2>&1; then
  GIT_COMMON="$(git -C "$PROJECT_DIR" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || git -C "$PROJECT_DIR" rev-parse --git-common-dir 2>/dev/null || true)"
  if [ -n "$GIT_COMMON" ]; then
    case "$GIT_COMMON" in
      /*) COMMON_ABS="$GIT_COMMON" ;;
      *) COMMON_ABS="$(CDPATH= cd -- "$PROJECT_DIR" && CDPATH= cd -- "$GIT_COMMON" 2>/dev/null && pwd || true)" ;;
    esac
    if [ -n "$COMMON_ABS" ]; then
      CAND_MAIN="$(CDPATH= cd -- "$COMMON_ABS/.." 2>/dev/null && pwd || true)"
      if [ -n "$CAND_MAIN" ] && [ -d "$CAND_MAIN/.agents" ]; then
        IGNORE_POLICY="$(read_setup_field "$PROJECT_DIR/.agents/setup-state.json" "ignore_policy")"
        [ -n "$IGNORE_POLICY" ] || IGNORE_POLICY="$(read_setup_field "$CAND_MAIN/.agents/setup-state.json" "ignore_policy")"
        if [ "$IGNORE_POLICY" != "shared" ]; then
          EFFECTIVE_ROOT="$CAND_MAIN"
        fi
      fi
    fi
  fi
fi

raw_tmp="${TMPDIR:-/tmp}"
raw_tmp="${raw_tmp%/}"
[ -n "$raw_tmp" ] || raw_tmp="/tmp"
rt_base="${FLOW_RUNTIME_DIR:-$raw_tmp/flow-runtime}"
rt_base="${rt_base%/}"
ws_id="$(printf '%s' "$EFFECTIVE_ROOT" | tr '\\' '/' | sed 's:/*$::; s/[^A-Za-z0-9._-]/_/g' | awk '{ n = length($0); print (n > 120 ? substr($0, n - 119) : $0) }')"
[ -n "$ws_id" ] || ws_id="default"
RUNTIME_WS_DIR="$rt_base/$ws_id"
mkdir -p "$RUNTIME_WS_DIR" 2>/dev/null || true
STATE_FILE="$RUNTIME_WS_DIR/studio-live-state.json"
READ_STATE_FILE="$STATE_FILE"
if [ ! -f "$READ_STATE_FILE" ] && [ -f "$PROJECT_DIR/.agents/studio-live-state.json" ]; then
  READ_STATE_FILE="$PROJECT_DIR/.agents/studio-live-state.json"
fi

PREV_DIGEST=""
PREV_ROLE=""
PREV_FLOW=""
PREV_CHAPTER=""
PREV_TASKS="[]"
if [ -f "$READ_STATE_FILE" ]; then
  PREV_META="$(awk '
    { buf = buf " " $0 }
    END {
      pd = ""; rl = ""; fl = ""; ch = ""; ts = "[]"
      if (match(buf, /"specDigest"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"specDigest"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); pd = s
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
      if (match(p, /\/specs\/[^\/]+/)) {
        s = substr(p, RSTART, RLENGTH); sub(/^\/specs\//, "", s); fl = s
      }
      if (match(p, /\/chapters\/[^\/]+/)) {
        s = substr(p, RSTART, RLENGTH); sub(/^\/chapters\//, "", s); ch = s
      }
      if (match(p, /\/tasks\/[^\/]+\.md$/)) {
        s = substr(p, RSTART, RLENGTH); sub(/^\/tasks\//, "", s); sub(/\.md$/, "", s)
        if (s != "index") {
          sub(/-.*$/, "", s)
          tk = s
        }
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

if [ -z "$FLOW_ID" ]; then
  BUNDLE_REL=".agents/bundles"
  DETECTED_ROOT="$(read_setup_field "$EFFECTIVE_ROOT/.agents/setup-state.json" "bundle_root")"
  [ -n "$DETECTED_ROOT" ] && BUNDLE_REL="$DETECTED_ROOT"
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
fi

ACTIVITY=""
if [ -n "$P_TOOL" ] && [ -n "$P_FILE" ]; then
  ACTIVITY="$P_TOOL $P_FILE"
elif [ -n "$P_TOOL" ]; then
  ACTIVITY="Running $P_TOOL"
fi

json_escape_str() {
  printf '%s' "$1" | awk '
    BEGIN { ORS = "" }
    {
      gsub(/\\/, "\\\\")
      gsub(/"/, "\\\"")
      gsub(/\t/, "\\t")
      gsub(/\r/, "")
      gsub(/[\001-\010\013\014\016-\037]/, "")
      if (NR > 1) printf "\\n"
      printf "%s", $0
    }
  '
}

WORKTREE_NORM="$(printf '%s' "$PROJECT_DIR" | tr '\\' '/' | sed 's:/*$::')"
NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")"

FLOW_JSON="null"
[ -n "$FLOW_ID" ] && FLOW_JSON="\"$(json_escape_str "$FLOW_ID")\""
CH_JSON="null"
[ -n "$CHAPTER_ID" ] && CH_JSON="\"$(json_escape_str "$CHAPTER_ID")\""

cat > "$STATE_FILE" <<EOF
{
  "v": 1,
  "updatedAt": "$NOW_ISO",
  "harness": "$(json_escape_str "$HARNESS")",
  "conversationId": "$(json_escape_str "$P_CONV")",
  "role": "$(json_escape_str "$ROLE")",
  "flowId": $FLOW_JSON,
  "chapterId": $CH_JSON,
  "taskIds": $TASK_IDS_JSON,
  "worktree": "$(json_escape_str "$WORKTREE_NORM")",
  "activity": "$(json_escape_str "$ACTIVITY")",
  "activeTurn": true,
  "lastTool": "$(json_escape_str "$P_TOOL")",
  "lastFilePath": "$(json_escape_str "$P_FILE")",
  "specDigest": "$(json_escape_str "$PREV_DIGEST")"
}
EOF

printf '{}\n'
