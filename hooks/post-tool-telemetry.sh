#!/usr/bin/env sh
# Portable POSIX sh + awk PostToolUse live telemetry writer for Flow Studio.
# Updates .agents/studio-live-state.json only when .agents/ exists in the workspace.
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
      fpath = s
    } else if (match(buf, /"file_path"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"file_path"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      fpath = s
    }

    gsub(/\|/, " ", ws)
    gsub(/\|/, " ", conv)
    gsub(/\|/, " ", tool_nm)
    gsub(/\|/, " ", fpath)
    printf "%s|%s|%s|%s\n", ws, conv, tool_nm, fpath
  }
')"

P_WS="${PARSED%%|*}"; R1="${PARSED#*|}"
P_CONV="${R1%%|*}"; R2="${R1#*|}"
P_TOOL="${R2%%|*}"; P_FILE="${R2#*|}"

if [ -z "$PROJECT_DIR" ]; then
  PROJECT_DIR="${P_WS:-$(pwd)}"
fi

if [ ! -d "$PROJECT_DIR/.agents" ]; then
  printf '{}\n'
  exit 0
fi

STATE_FILE="$PROJECT_DIR/.agents/studio-live-state.json"
PREV_DIGEST=""
if [ -f "$STATE_FILE" ]; then
  PREV_DIGEST="$(awk '
    { buf = buf " " $0 }
    END {
      if (match(buf, /"specDigest"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"specDigest"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        print s
      }
    }
  ' "$STATE_FILE")"
fi

NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")"

cat > "$STATE_FILE" <<EOF
{
  "updatedAt": "$NOW_ISO",
  "harness": "$HARNESS",
  "conversationId": "$P_CONV",
  "activeTurn": true,
  "lastTool": "$P_TOOL",
  "lastFilePath": "$P_FILE",
  "specDigest": "$PREV_DIGEST"
}
EOF

printf '{}\n'
