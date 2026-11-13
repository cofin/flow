#!/usr/bin/env sh
# Portable POSIX sh + awk PreInvocation refresh hook for Flow Studio.
# Emits {} unless an active spec.md or studio-comments.json changed on disk since last turn.
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

if [ -z "$PROJECT_DIR" ] && [ -n "$STDIN_PAYLOAD" ]; then
  PROJECT_DIR="$(printf '%s\n' "$STDIN_PAYLOAD" | awk '
    { buf = buf " " $0 }
    END {
      if (match(buf, /"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
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
      if (match(buf, /"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        print s
        exit
      }
    }
  ')"
fi

if [ -z "$PROJECT_DIR" ]; then
  PROJECT_DIR="$(pwd)"
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

BUNDLE_REL=".agents/bundles"
DETECTED_ROOT="$(read_setup_field "$EFFECTIVE_ROOT/.agents/setup-state.json" "bundle_root")"
if [ -n "$DETECTED_ROOT" ]; then
  BUNDLE_REL="$DETECTED_ROOT"
fi

DIGEST_ACC=""
if [ -d "$EFFECTIVE_ROOT/$BUNDLE_REL/specs" ]; then
  for spec_file in "$EFFECTIVE_ROOT/$BUNDLE_REL/specs"/*/spec.md; do
    [ -f "$spec_file" ] || continue
    ck_val="$(cksum "$spec_file" | awk '{ printf "%s:%s", $1, $2 }')"
    DIGEST_ACC="${DIGEST_ACC}${spec_file}=${ck_val};"
  done
fi
if [ -f "$EFFECTIVE_ROOT/.agents/studio-comments.json" ]; then
  ck_comments="$(cksum "$EFFECTIVE_ROOT/.agents/studio-comments.json" | awk '{ printf "%s:%s", $1, $2 }')"
  DIGEST_ACC="${DIGEST_ACC}comments=${ck_comments};"
fi

if [ -z "$DIGEST_ACC" ]; then
  printf '{}\n'
  exit 0
fi

FINAL_DIGEST="$(printf '%s' "$DIGEST_ACC" | cksum | awk '{ printf "%s-%s", $1, $2 }')"
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
      if (match(buf, /"activeTurn"[[:space:]]*:[[:space:]]*true/)) {
        at = "true"
      }
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

if [ -n "$STDIN_PAYLOAD" ]; then
  STDIN_META="$(printf '%s\n' "$STDIN_PAYLOAD" | awk '
    { buf = buf " " $0 }
    END {
      cv = ""; pc = ""
      if (match(buf, /"conversationId"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"conversationId"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); cv = s
      } else if (match(buf, /"session_id"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"session_id"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); cv = s
      }
      if (match(buf, /"parentConversationId"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH); sub(/^.*"parentConversationId"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); pc = s
      }
      printf "%s|%s\n", cv, pc
    }
  ')"
  S_CONV="${STDIN_META%%|*}"
  S_PARENT="${STDIN_META#*|}"
  [ -n "$S_CONV" ] && PREV_CONV="$S_CONV"
  [ -n "$S_PARENT" ] && PREV_ROLE="flow-subagent"
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

write_state_digest() {
  FLOW_JSON="null"
  [ -n "$PREV_FLOW" ] && FLOW_JSON="\"$(json_escape_str "$PREV_FLOW")\""
  CH_JSON="null"
  [ -n "$PREV_CHAPTER" ] && CH_JSON="\"$(json_escape_str "$PREV_CHAPTER")\""
  cat > "$STATE_FILE" <<EOF
{
  "v": 1,
  "updatedAt": "$NOW_ISO",
  "harness": "$(json_escape_str "$HARNESS")",
  "conversationId": "$(json_escape_str "$PREV_CONV")",
  "role": "$(json_escape_str "${PREV_ROLE:-coordinator}")",
  "flowId": $FLOW_JSON,
  "chapterId": $CH_JSON,
  "taskIds": ${PREV_TASKS:-[]},
  "worktree": "$(json_escape_str "$WORKTREE_NORM")",
  "activity": "$(json_escape_str "$PREV_ACTIVITY")",
  "activeTurn": $ACTIVE_TURN,
  "lastTool": "$(json_escape_str "$PREV_TOOL")",
  "lastFilePath": "$(json_escape_str "$PREV_FILE")",
  "specDigest": "$(json_escape_str "$FINAL_DIGEST")"
}
EOF
}

if [ -z "$PREV_DIGEST" ]; then
  write_state_digest
  printf '{}\n'
  exit 0
fi

if [ "$PREV_DIGEST" = "$FINAL_DIGEST" ] || [ "$ACTIVE_TURN" = "true" ]; then
  if [ "$PREV_DIGEST" != "$FINAL_DIGEST" ]; then
    write_state_digest
  fi
  printf '{}\n'
  exit 0
fi

write_state_digest

NOTICE_MSG="Flow Studio notice: Active spec.md or Studio review comments changed on disk since the previous turn. Re-read the active spec.md and .agents/studio-comments.json before mutating code."

case "$HARNESS" in
  agy|antigravity)
    printf '{"injectSteps":[{"systemMessage":{"systemMessage":"%s"}}]}\n' "$NOTICE_MSG"
    ;;
  cursor)
    printf '{"continue":true,"additional_context":"%s"}\n' "$NOTICE_MSG"
    ;;
  claude|vscode|*)
    printf '{"continue":true,"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"%s"}}\n' "$NOTICE_MSG"
    ;;
esac
