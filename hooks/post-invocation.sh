#!/usr/bin/env sh
# Portable POSIX sh + awk PostInvocation hook for Flow Studio.
# Clears activeTurn in .agents/studio-live-state.json when an invocation concludes.
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

STATE_FILE="$PROJECT_DIR/.agents/studio-live-state.json"
if [ ! -f "$STATE_FILE" ]; then
  printf '{}\n'
  exit 0
fi

PREV_META="$(awk '
  { buf = buf " " $0 }
  END {
    pd = ""
    lt = ""
    lf = ""
    if (match(buf, /"specDigest"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"specDigest"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); pd = s
    }
    if (match(buf, /"lastTool"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"lastTool"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); lt = s
    }
    if (match(buf, /"lastFilePath"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"lastFilePath"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); lf = s
    }
    printf "%s|%s|%s\n", pd, lt, lf
  }
' "$STATE_FILE")"

PREV_DIGEST="${PREV_META%%|*}"; RM1="${PREV_META#*|}"
PREV_TOOL="${RM1%%|*}"; PREV_FILE="${RM1#*|}"
NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")"

cat > "$STATE_FILE" <<EOF
{
  "updatedAt": "$NOW_ISO",
  "harness": "$HARNESS",
  "conversationId": "$P_CONV",
  "activeTurn": false,
  "lastTool": "$PREV_TOOL",
  "lastFilePath": "$PREV_FILE",
  "specDigest": "$PREV_DIGEST"
}
EOF

printf '{}\n'
