#!/usr/bin/env sh
# Portable POSIX sh + awk PostInvocation hook for Flow Studio.
# Clears activeTurn in ${FLOW_RUNTIME_DIR:-$TMPDIR/flow-runtime}/<ws_id>/studio-live-state.json when an invocation concludes.
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
    }
    gsub(/\|/, " ", ws)
    gsub(/\|/, " ", conv)
    printf "%s|%s\n", ws, conv
  }
')"

P_WS="${PARSED%%|*}"
P_CONV="${PARSED#*|}"

if [ -z "$PROJECT_DIR" ]; then
  PROJECT_DIR="${P_WS:-$(pwd)}"
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
STATE_FILE="$RUNTIME_WS_DIR/studio-live-state.json"
READ_STATE_FILE="$STATE_FILE"
if [ ! -f "$READ_STATE_FILE" ]; then
  if [ -f "$PROJECT_DIR/.agents/studio-live-state.json" ]; then
    READ_STATE_FILE="$PROJECT_DIR/.agents/studio-live-state.json"
  else
    printf '{}\n'
    exit 0
  fi
fi

mkdir -p "$RUNTIME_WS_DIR" 2>/dev/null || true

PREV_META="$(awk '
  { buf = buf " " $0 }
  END {
    pd = ""; lt = ""; lf = ""; rl = "coordinator"; fl = ""; ch = ""; ts = "[]"; act = ""
    if (match(buf, /"specDigest"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"specDigest"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); pd = s
    }
    if (match(buf, /"lastTool"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"lastTool"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); lt = s
    }
    if (match(buf, /"lastFilePath"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"lastFilePath"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); lf = s
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
[ -n "$PREV_FLOW" ] && FLOW_JSON="\"$(json_escape_str "$PREV_FLOW")\""
CH_JSON="null"
[ -n "$PREV_CHAPTER" ] && CH_JSON="\"$(json_escape_str "$PREV_CHAPTER")\""

cat > "$STATE_FILE" <<EOF
{
  "v": 1,
  "updatedAt": "$NOW_ISO",
  "harness": "$(json_escape_str "$HARNESS")",
  "conversationId": "$(json_escape_str "$P_CONV")",
  "role": "$(json_escape_str "${PREV_ROLE:-coordinator}")",
  "flowId": $FLOW_JSON,
  "chapterId": $CH_JSON,
  "taskIds": ${PREV_TASKS:-[]},
  "worktree": "$(json_escape_str "$WORKTREE_NORM")",
  "activity": "$(json_escape_str "$PREV_ACTIVITY")",
  "activeTurn": false,
  "lastTool": "$(json_escape_str "$PREV_TOOL")",
  "lastFilePath": "$(json_escape_str "$PREV_FILE")",
  "specDigest": "$(json_escape_str "$PREV_DIGEST")"
}
EOF

printf '{}\n'
