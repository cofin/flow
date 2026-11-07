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

record_recent_workspace() {
  ws_dir="$1"
  [ -n "$ws_dir" ] || return 0
  [ -d "$ws_dir/.agents" ] || [ -e "$ws_dir/.git" ] || [ -d "$ws_dir/.jj" ] || [ -d "$ws_dir/.hg" ] || return 0
  if [ -z "${FLOW_CONFIG_DIR:-}" ]; then
    case "$ws_dir" in
      /tmp/*|/var/folders/*|*/pytest-of-*|*/Temp/*|*/sidecars/studio|*/.gemini/config/plugins/*)
        return 0
        ;;
    esac
  fi
  cfg_dir="${FLOW_CONFIG_DIR:-${XDG_CONFIG_HOME:-${HOME:-/tmp}/.config}/flow}"
  mkdir -p "$cfg_dir" 2>/dev/null || return 0
  ts_iso="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "2026-01-01T00:00:00Z")"
  printf '%s\t%s\n' "$ts_iso" "$ws_dir" >> "$cfg_dir/recent-workspaces.tsv" 2>/dev/null || true
}
record_recent_workspace "$PROJECT_DIR"

if [ ! -d "$PROJECT_DIR/.agents" ]; then
  printf '{}\n'
  exit 0
fi

BUNDLE_REL=".agents/bundles"
if [ -f "$PROJECT_DIR/.agents/setup-state.json" ]; then
  DETECTED_ROOT="$(awk '
    { buf = buf " " $0 }
    END {
      if (match(buf, /"bundle_root"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"bundle_root"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        print s
      }
    }
  ' "$PROJECT_DIR/.agents/setup-state.json")"
  if [ -n "$DETECTED_ROOT" ]; then
    BUNDLE_REL="$DETECTED_ROOT"
  fi
fi

DIGEST_ACC=""
if [ -d "$PROJECT_DIR/$BUNDLE_REL/specs" ]; then
  for spec_file in "$PROJECT_DIR/$BUNDLE_REL/specs"/*/spec.md; do
    [ -f "$spec_file" ] || continue
    ck_val="$(cksum "$spec_file" | awk '{ printf "%s:%s", $1, $2 }')"
    DIGEST_ACC="${DIGEST_ACC}${spec_file}=${ck_val};"
  done
fi
if [ -f "$PROJECT_DIR/.agents/studio-comments.json" ]; then
  ck_comments="$(cksum "$PROJECT_DIR/.agents/studio-comments.json" | awk '{ printf "%s:%s", $1, $2 }')"
  DIGEST_ACC="${DIGEST_ACC}comments=${ck_comments};"
fi

if [ -z "$DIGEST_ACC" ]; then
  printf '{}\n'
  exit 0
fi

FINAL_DIGEST="$(printf '%s' "$DIGEST_ACC" | cksum | awk '{ printf "%s-%s", $1, $2 }')"
STATE_FILE="$PROJECT_DIR/.agents/studio-live-state.json"
PREV_DIGEST=""
ACTIVE_TURN="false"

if [ -f "$STATE_FILE" ]; then
  STATE_PARSED="$(awk '
    { buf = buf " " $0 }
    END {
      pd = ""
      at = "false"
      if (match(buf, /"specDigest"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"specDigest"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        pd = s
      }
      if (match(buf, /"activeTurn"[[:space:]]*:[[:space:]]*true/)) {
        at = "true"
      }
      printf "%s|%s\n", pd, at
    }
  ' "$STATE_FILE")"
  PREV_DIGEST="${STATE_PARSED%%|*}"
  ACTIVE_TURN="${STATE_PARSED#*|}"
fi

NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")"

write_state_digest() {
  cat > "$STATE_FILE" <<EOF
{
  "updatedAt": "$NOW_ISO",
  "harness": "$HARNESS",
  "activeTurn": $ACTIVE_TURN,
  "specDigest": "$FINAL_DIGEST"
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
