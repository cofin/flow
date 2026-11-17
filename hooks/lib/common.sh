#!/usr/bin/env sh
# Shared POSIX sh + awk utilities for Flow runtime hooks.
# Sourced by hooks/*.sh; defines helper functions without mutating shell exit state on load.

flow_parse_args() {
  DEFAULT_HARNESS="${1:-claude}"
  HARNESS="$DEFAULT_HARNESS"
  PROJECT_DIR=""
  shift || true
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --harness)
        HARNESS="${2:-$DEFAULT_HARNESS}"
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
}

flow_read_stdin() {
  STDIN_PAYLOAD=""
  if [ ! -t 0 ]; then
    STDIN_PAYLOAD="$(cat || true)"
  fi
}

flow_json_escape() {
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

flow_strip_xml_tags() {
  printf '%s' "$1" | sed -e 's/<[^>]*>//g'
}

flow_extract_payload_field() {
  payload="$1"
  key="$2"
  printf '%s\n' "$payload" | awk -v k="$key" '
    { buf = buf " " $0 }
    END {
      pat = "\"" k "\"[[:space:]]*:[[:space:]]*\"([^\"]*)\""
      if (match(buf, pat)) {
        s = substr(buf, RSTART, RLENGTH)
        sub("^.*\"" k "\"[[:space:]]*:[[:space:]]*\"", "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        print s
      }
    }
  '
}

flow_resolve_project_dir() {
  if [ -z "${PROJECT_DIR:-}" ] && [ -n "${STDIN_PAYLOAD:-}" ]; then
    PROJECT_DIR="$(printf '%s\n' "$STDIN_PAYLOAD" | awk '
      { buf = buf " " $0 }
      END {
        proj = ""
        if (match(buf, /"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
          s = substr(buf, RSTART, RLENGTH); sub(/^.*"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); proj = s
        } else if (match(buf, /"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
          s = substr(buf, RSTART, RLENGTH); sub(/^.*"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); proj = s
        } else if (match(buf, /"cwd"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
          s = substr(buf, RSTART, RLENGTH); sub(/^.*"cwd"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); proj = s
        } else if (match(buf, /"workspaceRoot"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
          s = substr(buf, RSTART, RLENGTH); sub(/^.*"workspaceRoot"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); proj = s
        }
        print proj
      }
    ')"
  fi
  if [ -z "${PROJECT_DIR:-}" ]; then
    if [ -n "${CURSOR_PROJECT_DIR:-}" ]; then
      PROJECT_DIR="$CURSOR_PROJECT_DIR"
    elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
      PROJECT_DIR="$CLAUDE_PROJECT_DIR"
    else
      PROJECT_DIR="$(pwd)"
    fi
  fi
}

flow_read_setup_field() {
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

flow_resolve_worktree_context() {
  IS_LINKED_WORKTREE=0
  MAIN_WORKTREE=""
  EFFECTIVE_ROOT="$PROJECT_DIR"
  IGNORE_POLICY=""

  if [ -f "$PROJECT_DIR/.git" ] && command -v git >/dev/null 2>&1; then
    GIT_COMMON="$(git -C "$PROJECT_DIR" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || git -C "$PROJECT_DIR" rev-parse --git-common-dir 2>/dev/null || true)"
    if [ -n "$GIT_COMMON" ]; then
      case "$GIT_COMMON" in
        /*) COMMON_ABS="$GIT_COMMON" ;;
        *) COMMON_ABS="$(CDPATH= cd -- "$PROJECT_DIR" && CDPATH= cd -- "$GIT_COMMON" 2>/dev/null && pwd || true)" ;;
      esac
      if [ -n "$COMMON_ABS" ]; then
        CAND_MAIN="$(CDPATH= cd -- "$COMMON_ABS/.." 2>/dev/null && pwd || true)"
        PROJ_ABS="$(CDPATH= cd -- "$PROJECT_DIR" 2>/dev/null && pwd || printf '%s' "$PROJECT_DIR")"
        if [ -n "$CAND_MAIN" ] && [ "$CAND_MAIN" != "$PROJ_ABS" ]; then
          IS_LINKED_WORKTREE=1
          MAIN_WORKTREE="$CAND_MAIN"
        fi
      fi
    fi
  fi

  if [ "$IS_LINKED_WORKTREE" = "1" ] && [ -n "$MAIN_WORKTREE" ]; then
    IGNORE_POLICY="$(flow_read_setup_field "$PROJECT_DIR/.agents/setup-state.json" "ignore_policy")"
    [ -n "$IGNORE_POLICY" ] || IGNORE_POLICY="$(flow_read_setup_field "$MAIN_WORKTREE/.agents/setup-state.json" "ignore_policy")"
    if [ -z "$IGNORE_POLICY" ]; then
      if [ -d "$PROJECT_DIR/.agents" ] && [ ! -L "$PROJECT_DIR/.agents" ] && git -C "$PROJECT_DIR" ls-files --error-unmatch .agents/bundles/index.md >/dev/null 2>&1; then
        IGNORE_POLICY="shared"
      elif [ -d "$MAIN_WORKTREE/.agents" ]; then
        IGNORE_POLICY="local-only"
      else
        IGNORE_POLICY="shared"
      fi
    fi
    if [ "$IGNORE_POLICY" = "local-only" ] && [ -d "$MAIN_WORKTREE/.agents" ]; then
      EFFECTIVE_ROOT="$MAIN_WORKTREE"
    fi
  fi

  BUNDLE_REL=".agents/bundles"
  DETECTED_ROOT="$(flow_read_setup_field "$EFFECTIVE_ROOT/.agents/setup-state.json" "bundle_root")"
  if [ -n "$DETECTED_ROOT" ]; then
    BUNDLE_REL="$DETECTED_ROOT"
  fi
}

flow_runtime_paths() {
  raw_tmp="${TMPDIR:-/tmp}"
  raw_tmp="${raw_tmp%/}"
  [ -n "$raw_tmp" ] || raw_tmp="/tmp"
  RT_BASE="${FLOW_RUNTIME_DIR:-$raw_tmp/flow-runtime}"
  RT_BASE="${RT_BASE%/}"
  WS_ID="$(printf '%s' "$EFFECTIVE_ROOT" | tr '\\' '/' | sed 's:/*$::; s/[^A-Za-z0-9._-]/_/g' | awk '{ n = length($0); print (n > 120 ? substr($0, n - 119) : $0) }')"
  [ -n "$WS_ID" ] || WS_ID="default"
  RUNTIME_WS_DIR="$RT_BASE/$WS_ID"
  STATE_FILE="$RUNTIME_WS_DIR/studio-live-state.json"
  READ_STATE_FILE="$STATE_FILE"
  if [ ! -f "$READ_STATE_FILE" ] && [ -f "$PROJECT_DIR/.agents/studio-live-state.json" ]; then
    READ_STATE_FILE="$PROJECT_DIR/.agents/studio-live-state.json"
  fi
}

flow_detect_worker_invocation() {
  IS_WORKER_AGENT=0
  if [ "${FLOW_SWARM_WORKER:-}" = "1" ] || [ "${BB_SWARM_WORKER:-}" = "1" ]; then
    IS_WORKER_AGENT=1
    return 0
  fi

  if [ -n "${STDIN_PAYLOAD:-}" ]; then
    WORKER_FROM_STDIN="$(printf '%s\n' "$STDIN_PAYLOAD" | awk '
      { buf = buf " " $0 }
      END {
        if (match(buf, /"(parentConversationId|parent_conversation_id|parentSessionId|parent_session_id)"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
          print "1"; exit
        }
        if (match(buf, /"(agentName|agent_type|subagent_type)"[[:space:]]*:[[:space:]]*"(flow-|bb-|runtime-)[^"]*"/)) {
          print "1"; exit
        }
        if (match(buf, /"lastUserInput"[[:space:]]*:[[:space:]]*"[^"]*(agents\/(executor|researcher|code-reviewer|quality-reviewer|plan-generator)\.md|templates\/agent\/(plan|executor)-schema-card\.md|\.agents\/agents\/|\[Flow Swarm Worker\]|swarm-worker)/)) {
          print "1"; exit
        }
        print "0"
      }
    ')"
    if [ "$WORKER_FROM_STDIN" = "1" ]; then
      IS_WORKER_AGENT=1
      return 0
    fi

    TRANSCRIPT_P="$(flow_extract_payload_field "$STDIN_PAYLOAD" "transcriptPath")"
    if [ -n "$TRANSCRIPT_P" ] && [ -f "$TRANSCRIPT_P" ]; then
      IS_SYS_ONLY="$(awk '
        /"type"[[:space:]]*:[[:space:]]*"USER_INPUT"/ { has_user = 1; exit }
        /"type"[[:space:]]*:[[:space:]]*"SYSTEM_MESSAGE"/ { has_sys = 1 }
        END { print (has_sys && !has_user) ? "1" : "0" }
      ' "$TRANSCRIPT_P" 2>/dev/null || echo "0")"
      if [ "$IS_SYS_ONLY" = "1" ]; then
        IS_WORKER_AGENT=1
        return 0
      fi
    fi
  fi
}

flow_sibling_plugin_present() {
  if [ -n "${FLOW_SIBLING_PLUGIN_PRESENT:-}" ]; then
    [ "$FLOW_SIBLING_PLUGIN_PRESENT" = "1" ] && return 0 || return 1
  fi
  if [ -d "${HOME:-}/.gemini/config/plugins/bb" ] || [ -d "${HOME:-}/.gemini/jetski/plugins/bb" ] || [ -d "${EFFECTIVE_ROOT:-}/.agents/plugins/bb" ]; then
    return 0
  fi
  return 1
}
