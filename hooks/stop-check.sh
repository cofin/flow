#!/usr/bin/env sh
# Portable POSIX sh + awk + git Stop review & present-tense Markdown sync hook for Flow.
# Requires zero python3, node, or jq on the host system.
set -eu

HARNESS="claude"
PROJECT_DIR=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --harness)
      HARNESS="${2:-claude}"
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

emit_allow() {
  if [ "$HARNESS" = "json" ]; then
    printf '{"blocked":false,"reason":""}\n'
  else
    printf '{}\n'
  fi
  exit 0
}

# Suppress third-party Claude hook double-firing inside Cursor when native Cursor hook is active.
if [ "$HARNESS" = "claude" ] && [ -n "${CURSOR_VERSION:-}" ]; then
  emit_allow
fi

STOP_GATE_ENV="$(printf '%s' "${FLOW_STOP_GATE:-}" | tr '[:upper:]' '[:lower:]')"
case "$STOP_GATE_ENV" in
  off|0|false|no|advisory|warn)
    emit_allow
    ;;
esac

STDIN_PAYLOAD=""
if [ ! -t 0 ]; then
  STDIN_PAYLOAD="$(cat || true)"
fi

IS_LEAF_SUBAGENT=0
CONV_ID=""
BYPASS_FLAG=0
if [ -n "$STDIN_PAYLOAD" ]; then
  PARSED_STDIN="$(printf '%s\n' "$STDIN_PAYLOAD" | awk -v harness="$HARNESS" '
    { buf = buf " " $0 }
    END {
      proj = ""
      if (match(buf, /"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        proj = s
      } else if (match(buf, /"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        proj = s
      } else if (match(buf, /"cwd"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"cwd"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        proj = s
      } else if (match(buf, /"workspaceRoot"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"workspaceRoot"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        gsub(/\\\\/, "/", s)
        proj = s
      }

      conv = ""
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

      bypass = 0
      if (harness == "agy" || harness == "antigravity") {
        if (match(buf, /"terminationReason"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
          tr = substr(buf, RSTART, RLENGTH)
          sub(/^.*"terminationReason"[[:space:]]*:[[:space:]]*"/, "", tr)
          sub(/"$/, "", tr)
          if (tr != "" && tr != "model_stop") bypass = 1
        }
        if (match(buf, /"error"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
          bypass = 1
        }
        if (match(buf, /"executionNum"[[:space:]]*:[[:space:]]*[0-9]+/)) {
          en = substr(buf, RSTART, RLENGTH)
          sub(/^.*"executionNum"[[:space:]]*:[[:space:]]*/, "", en)
          if ((en + 0) >= 2) bypass = 1
        }
      } else if (harness == "cursor") {
        if (match(buf, /"status"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
          st = substr(buf, RSTART, RLENGTH)
          sub(/^.*"status"[[:space:]]*:[[:space:]]*"/, "", st)
          sub(/"$/, "", st)
          if (st != "" && st != "completed") bypass = 1
        }
        if (match(buf, /"loop_count"[[:space:]]*:[[:space:]]*[0-9]+/)) {
          lc = substr(buf, RSTART, RLENGTH)
          sub(/^.*"loop_count"[[:space:]]*:[[:space:]]*/, "", lc)
          if ((lc + 0) >= 1) bypass = 1
        }
      } else {
        if (match(buf, /"stop_hook_active"[[:space:]]*:[[:space:]]*true/)) {
          bypass = 1
        }
      }

      leaf = 0
      if (match(buf, /"parentConversationId"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        leaf = 1
      }
      if (match(buf, /"agentName"[[:space:]]*:[[:space:]]*"runtime-[^"]+"/)) {
        leaf = 1
      }
      if (match(buf, /"lastUserInput"[[:space:]]*:[[:space:]]*"[^"]*(agents\/(executor|researcher|code-reviewer|quality-reviewer|plan-generator)\.md|templates\/agent\/(plan|executor)-schema-card\.md|\.agents\/agents\/|\[Flow Swarm Worker\]|swarm-worker)/)) {
        leaf = 1
      }

      gsub(/\|/, "_", proj)
      gsub(/\|/, "_", conv)
      printf "%d|%d|%s|%s\n", bypass, leaf, proj, conv
    }
  ')"

  BYPASS_FLAG="${PARSED_STDIN%%|*}"
  REST_STDIN="${PARSED_STDIN#*|}"
  IS_LEAF_SUBAGENT="${REST_STDIN%%|*}"
  REST_STDIN2="${REST_STDIN#*|}"
  DETECTED_PROJ="${REST_STDIN2%%|*}"
  CONV_ID="${REST_STDIN2#*|}"

  if [ "$BYPASS_FLAG" = "1" ]; then
    emit_allow
  fi
  if [ -z "$PROJECT_DIR" ] && [ -n "$DETECTED_PROJ" ]; then
    PROJECT_DIR="$DETECTED_PROJ"
  fi
fi

if [ "${FLOW_SWARM_WORKER:-0}" = "1" ]; then
  IS_LEAF_SUBAGENT=1
fi

if [ -z "$PROJECT_DIR" ]; then
  if [ -n "${CURSOR_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CURSOR_PROJECT_DIR"
  elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CLAUDE_PROJECT_DIR"
  else
    PROJECT_DIR="$(pwd)"
  fi
fi

EFFECTIVE_ROOT="$PROJECT_DIR"
if [ ! -d "$PROJECT_DIR/.agents" ] && [ -f "$PROJECT_DIR/.git" ] && command -v git >/dev/null 2>&1; then
  GIT_COMMON="$(git -C "$PROJECT_DIR" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || git -C "$PROJECT_DIR" rev-parse --git-common-dir 2>/dev/null || true)"
  if [ -n "$GIT_COMMON" ]; then
    case "$GIT_COMMON" in
      /*) COMMON_ABS="$GIT_COMMON" ;;
      *) COMMON_ABS="$(CDPATH= cd -- "$PROJECT_DIR" && CDPATH= cd -- "$GIT_COMMON" 2>/dev/null && pwd || true)" ;;
    esac
    if [ -n "$COMMON_ABS" ]; then
      CAND_MAIN="$(CDPATH= cd -- "$COMMON_ABS/.." 2>/dev/null && pwd || true)"
      if [ -n "$CAND_MAIN" ] && [ -d "$CAND_MAIN/.agents" ]; then
        EFFECTIVE_ROOT="$CAND_MAIN"
      fi
    fi
  fi
fi

get_runtime_lease_dir() {
  raw_tmp="${TMPDIR:-/tmp}"
  raw_tmp="${raw_tmp%/}"
  [ -n "$raw_tmp" ] || raw_tmp="/tmp"
  rt_base="${FLOW_RUNTIME_DIR:-$raw_tmp/flow-runtime}"
  rt_base="${rt_base%/}"
  ws_id="$(printf '%s' "$EFFECTIVE_ROOT" | tr '\\' '/' | sed 's:/*$::; s/[^A-Za-z0-9._-]/_/g' | awk '{ n = length($0); print (n > 120 ? substr($0, n - 119) : $0) }')"
  [ -n "$ws_id" ] || ws_id="default"
  printf '%s/%s/subagents\n' "$rt_base" "$ws_id"
}

SUBAGENT_LEASE_DIR="$(get_runtime_lease_dir)"
SAFE_CONV=""
if [ -n "$CONV_ID" ]; then
  SAFE_CONV="$(printf '%s' "$CONV_ID" | sed 's/[^A-Za-z0-9._-]/_/g')"
fi

if [ "$IS_LEAF_SUBAGENT" = "1" ]; then
  if [ -n "$SAFE_CONV" ] && [ -f "$SUBAGENT_LEASE_DIR/$SAFE_CONV.lease" ]; then
    rm -f "$SUBAGENT_LEASE_DIR/$SAFE_CONV.lease" 2>/dev/null || true
  fi
  emit_allow
fi

BUNDLE_REL=".agents/bundles"
STOP_GATE_CFG="enforce"
SHA_TRACKING="strict"
if [ -f "$EFFECTIVE_ROOT/.agents/setup-state.json" ]; then
  SETUP_PARSED="$(awk '
    { buf = buf " " $0 }
    END {
      br = ""; sg = ""; st = ""
      if (match(buf, /"bundle_root"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"bundle_root"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        br = s
      }
      if (match(buf, /"stop_gate"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"stop_gate"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        sg = tolower(s)
      }
      if (match(buf, /"sha_tracking"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
        s = substr(buf, RSTART, RLENGTH)
        sub(/^.*"sha_tracking"[[:space:]]*:[[:space:]]*"/, "", s)
        sub(/"$/, "", s)
        st = tolower(s)
      }
      printf "%s|%s|%s\n", br, sg, st
    }
  ' "$EFFECTIVE_ROOT/.agents/setup-state.json")"
  DETECTED_ROOT="${SETUP_PARSED%%|*}"; s_rest="${SETUP_PARSED#*|}"
  DETECTED_GATE="${s_rest%%|*}"; DETECTED_SHA="${s_rest#*|}"
  [ -n "$DETECTED_ROOT" ] && BUNDLE_REL="$DETECTED_ROOT"
  [ -n "$DETECTED_GATE" ] && STOP_GATE_CFG="$DETECTED_GATE"
  [ -n "$DETECTED_SHA" ] && SHA_TRACKING="$DETECTED_SHA"
fi

case "$STOP_GATE_CFG" in
  off|0|false|no|advisory|warn)
    emit_allow
    ;;
esac

case "$SHA_TRACKING" in
  strict|advisory|off) ;;
  *) SHA_TRACKING="strict" ;;
esac

if [ -d "$SUBAGENT_LEASE_DIR" ]; then
  NOW_EPOCH="$(date -u +%s 2>/dev/null || echo 0)"
  for lf in "$SUBAGENT_LEASE_DIR"/*.lease; do
    [ -f "$lf" ] || continue
    lf_base="$(basename "$lf" .lease)"
    lf_ts="$(head -n 1 "$lf" 2>/dev/null | tr -dc '0-9' || true)"
    if [ -z "$lf_ts" ] || [ $((NOW_EPOCH - lf_ts)) -gt 900 ]; then
      rm -f "$lf" 2>/dev/null || true
      continue
    fi
    if [ -z "$SAFE_CONV" ] || [ "$lf_base" != "$SAFE_CONV" ]; then
      emit_allow
    fi
  done
fi

if [ -n "$CONV_ID" ]; then
  RUNTIME_LIVE_STATE="$(dirname "$SUBAGENT_LEASE_DIR")/studio-live-state.json"
  for live_cand in "$RUNTIME_LIVE_STATE" "$EFFECTIVE_ROOT/.agents/studio-live-state.json" "$PROJECT_DIR/.agents/studio-live-state.json"; do
    [ -f "$live_cand" ] || continue
    if [ -n "$(find "$live_cand" -mmin -10 2>/dev/null || true)" ]; then
      LIVE_OTHER="$(awk -v self_conv="$CONV_ID" '
        { buf = buf " " $0 }
        END {
          act = (match(buf, /"activeTurn"[[:space:]]*:[[:space:]]*true/) ? 1 : 0)
          conv = ""
          if (match(buf, /"conversationId"[[:space:]]*:[[:space:]]*"[^"]*"/)) {
            s = substr(buf, RSTART, RLENGTH)
            sub(/^.*"conversationId"[[:space:]]*:[[:space:]]*"/, "", s)
            sub(/"$/, "", s)
            conv = s
          }
          if (act == 1 && conv != "" && conv != self_conv) print "1"
        }
      ' "$live_cand")"
      if [ "$LIVE_OTHER" = "1" ]; then
        emit_allow
      fi
    fi
    break
  done
fi

SPECS_DIR="$EFFECTIVE_ROOT/$BUNDLE_REL/specs"
if [ ! -d "$SPECS_DIR" ]; then
  emit_allow
fi

HAS_GIT=0
if command -v git >/dev/null 2>&1 && git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  HAS_GIT=1
fi

VIOLATIONS=""
append_violation() {
  if [ -n "$VIOLATIONS" ]; then
    VIOLATIONS="$VIOLATIONS; $1"
  else
    VIOLATIONS="$1"
  fi
}

check_living_doc_hygiene() {
  doc_file="$1"
  rel_label="$2"
  is_index_file="$3"
  DOC_ERR="$(awk -v v_rel="$rel_label" -v v_is_idx="$is_index_file" '
    NR == 1 && /^---[[:space:]]*$/ {
      if (v_is_idx == "1") {
        printf "%s: subdirectory index.md must not contain YAML frontmatter", v_rel
        exit
      }
      in_fm = 1
      next
    }
    in_fm && /^---[[:space:]]*$/ {
      in_fm = 0
      in_src = 0
      next
    }
    in_fm {
      if (/^status:[[:space:]]*/) {
        sv = $0; sub(/^status:[[:space:]]*/, "", sv); sub(/[[:space:]]+#.*$/, "", sv); gsub(/^["'\'']|["'\'']$/, "", sv); gsub(/[[:space:]]+$/, "", sv)
        if (sv != "" && sv != "draft" && sv != "stable" && sv != "deprecated") {
          err = sprintf("%s: invalid OKF status \x27%s\x27 (expected draft, stable, or deprecated; use state for workflow lifecycle)", v_rel, sv)
          exit
        }
      }
      if (/^planning_quality:[[:space:]]*/) {
        pq = $0; sub(/^planning_quality:[[:space:]]*/, "", pq); sub(/[[:space:]]+#.*$/, "", pq); gsub(/^["'\'']|["'\'']$/, "", pq); gsub(/[[:space:]]+$/, "", pq)
      }
      if (/^planning_degraded_reason:[[:space:]]*/) {
        pdr = $0; sub(/^planning_degraded_reason:[[:space:]]*/, "", pdr); sub(/[[:space:]]+#.*$/, "", pdr); gsub(/^["'\'']|["'\'']$/, "", pdr); gsub(/[[:space:]]+$/, "", pdr)
      }
      if (/^sources:[[:space:]]*$/) {
        in_src = 1
        next
      }
      if (in_src && /^[^[:space:]-]/) {
        in_src = 0
      }
      if (in_src && /^[[:space:]]*-[[:space:]]*id:[[:space:]]*/) {
        sid = $0; sub(/^[[:space:]]*-[[:space:]]*id:[[:space:]]*/, "", sid); sub(/[[:space:]]+#.*$/, "", sid); gsub(/^["'\'']|["'\'']$/, "", sid); gsub(/[[:space:]]+$/, "", sid)
        if (sid != "") { src_count++; src_ids[src_count] = sid }
      } else if (in_src && /^[[:space:]]+id:[[:space:]]*/) {
        sid = $0; sub(/^[[:space:]]+id:[[:space:]]*/, "", sid); sub(/[[:space:]]+#.*$/, "", sid); gsub(/^["'\'']|["'\'']$/, "", sid); gsub(/[[:space:]]+$/, "", sid)
        if (sid != "") { src_count++; src_ids[src_count] = sid }
      }
      next
    }
    /^[[:space:]]*(```|~~~)/ {
      in_fence = !in_fence
      next
    }
    in_fence { next }
    /^\[\^[^]]+\]:/ {
      fn = $0; sub(/^\[\^/, "", fn); sub(/\]:.*$/, "", fn)
      fn_defs[fn] = 1
    }
    /^[[:space:]]*---[[:space:]]*$/ {
      err = sprintf("%s: standalone --- horizontal rule forbidden in bundle Markdown body", v_rel)
      exit
    }
    tolower($0) ~ /^[[:space:]]*#+[[:space:]]*(revision history|change history|changelog|decision history)([[:space:]:]|$)/ {
      err = sprintf("%s: historical changelog/revision section forbidden in present-tense living spec", v_rel)
      exit
    }
    /^[[:space:]]*-[[:space:]]*\[[^]]*\][[:space:]]*~~/ {
      err = sprintf("%s: struck-through obsolete checklist item forbidden; rewrite in place in present tense", v_rel)
      exit
    }
    END {
      if (err != "") {
        printf "%s", err
        exit
      }
      if (pq == "degraded" && (pdr == "" || pdr == "null" || pdr == "~")) {
        printf "%s: planning_quality is degraded without non-empty planning_degraded_reason", v_rel
        exit
      }
      for (k = 1; k <= src_count; k++) {
        want_fn = src_ids[k]
        if (!(want_fn in fn_defs)) {
          printf "%s: source id \x27%s\x27 missing matching [^%s]: footnote in body", v_rel, want_fn, want_fn
          exit
        }
      }
    }
  ' "$doc_file")"
  if [ -n "$DOC_ERR" ]; then
    append_violation "$DOC_ERR"
  fi
}

check_tasks_against_spec() {
  owner_spec="$1"
  tasks_dir="$2"
  scope_label="$3"

  TASK_TOTAL=0
  TASK_DONE=0
  COMPLETED_SHAS=""

  if [ ! -d "$tasks_dir" ]; then
    return 0
  fi

  for task_file in "$tasks_dir"/*.md; do
    [ -f "$task_file" ] || continue
    task_base="$(basename "$task_file")"
    [ "$task_base" = "index.md" ] && continue

    TASK_TOTAL=$((TASK_TOTAL + 1))
    TASK_META="$(awk '
      function push_owned(raw,    n, arr, idx, item) {
        sub(/^\[/, "", raw); sub(/\][[:space:]]*$/, "", raw)
        n = split(raw, arr, ",")
        for (idx = 1; idx <= n; idx++) {
          item = arr[idx]
          gsub(/^[[:space:]]*["'\'']?|["'\'']?[[:space:]]*$/, "", item)
          sub(/::.*$/, "", item)
          if (item != "" && item != "null" && item != "~") {
            owned = (owned == "" ? item : owned ";" item)
          }
        }
      }
      NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
      in_fm && /^---[[:space:]]*$/ { exit }
      in_fm && /^id:[[:space:]]*/ {
        v = $0; sub(/^id:[[:space:]]*/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); id = v; list_key = ""; next
      }
      in_fm && /^state:[[:space:]]*/ {
        v = $0; sub(/^state:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); st = v; list_key = ""; next
      }
      in_fm && /^commit:[[:space:]]*/ {
        v = $0; sub(/^commit:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); cm = v; list_key = ""; next
      }
      in_fm && /^deferred_by:[[:space:]]*/ {
        v = $0; sub(/^deferred_by:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); dby = v; list_key = ""; next
      }
      in_fm && /^deferred_reason:[[:space:]]*/ {
        v = $0; sub(/^deferred_reason:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); drsn = v; list_key = ""; next
      }
      in_fm && /^(files|tests):[[:space:]]*/ {
        v = $0; sub(/^(files|tests):[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/[[:space:]]+$/, "", v)
        if (v == "") {
          list_key = "owned"
        } else {
          list_key = ""
          push_owned(v)
        }
        next
      }
      in_fm && /^[^[:space:]-]/ {
        list_key = ""
      }
      in_fm && list_key == "owned" && /^[[:space:]]*-[[:space:]]+/ {
        v = $0; sub(/^[[:space:]]*-[[:space:]]+/, "", v); sub(/[[:space:]]+#.*$/, "", v)
        push_owned(v)
      }
      END { printf "%s|%s|%s|%s|%s|%s\n", id, st, cm, dby, drsn, owned }
    ' "$task_file")"

    t_id="${TASK_META%%|*}"; t_r1="${TASK_META#*|}"
    t_state="${t_r1%%|*}"; t_r2="${t_r1#*|}"
    t_commit="${t_r2%%|*}"; t_r3="${t_r2#*|}"
    t_def_by="${t_r3%%|*}"; t_r4="${t_r3#*|}"
    t_def_reason="${t_r4%%|*}"; t_owned="${t_r4#*|}"
    t_stem="${task_base%%-*}"
    [ -z "$t_id" ] && t_id="$t_stem"

    case "$t_state" in
      completed|closed)
        expected_mark="x"
        TASK_DONE=$((TASK_DONE + 1))
        case "$t_commit" in
          ""|null|~)
            append_violation "$scope_label/$task_base: state is $t_state but commit SHA is missing"
            ;;
          *)
            if ! printf '%s\n' "$t_commit" | grep -Eq '^[0-9a-fA-F]{7,40}$'; then
              append_violation "$scope_label/$task_base: invalid hex commit SHA '$t_commit'"
            else
              COMPLETED_SHAS="$COMPLETED_SHAS $t_commit"
              if [ "$SHA_TRACKING" != "off" ] && [ "$HAS_GIT" = "1" ] && [ -n "$t_owned" ] && git -C "$PROJECT_DIR" cat-file -e "${t_commit}^{commit}" 2>/dev/null; then
                DIFF_FILES="$(git -C "$PROJECT_DIR" diff-tree --no-commit-id --name-only -r --root "$t_commit" 2>/dev/null || true)"
                OWNED_OK="$(printf '%s\n' "$DIFF_FILES" | awk -v v_owned="$t_owned" '
                  BEGIN {
                    cnt = split(v_owned, targets, ";")
                  }
                  NF > 0 {
                    changed = $0
                    for (i = 1; i <= cnt; i++) {
                      t = targets[i]
                      sub(/^\.\//, "", t)
                      if (t == "") continue
                      if (changed == t || index(changed, t "/") == 1 || index(t, changed "/") == 1) {
                        matched = 1
                        exit
                      }
                    }
                  }
                  END { print (matched ? "1" : "0") }
                ')"
                if [ "$OWNED_OK" = "0" ]; then
                  old_ifs="$IFS"
                  IFS=";"
                  NON_IGNORED_OWNED=""
                  for raw_own in $t_owned; do
                    clean_own="${raw_own#./}"
                    [ -n "$clean_own" ] || continue
                    if ! git -C "$PROJECT_DIR" check-ignore -q -- "$clean_own" 2>/dev/null; then
                      if [ -n "$NON_IGNORED_OWNED" ]; then
                        NON_IGNORED_OWNED="$NON_IGNORED_OWNED;$clean_own"
                      else
                        NON_IGNORED_OWNED="$clean_own"
                      fi
                    fi
                  done
                  IFS="$old_ifs"
                  if [ -n "$NON_IGNORED_OWNED" ]; then
                    append_violation "$scope_label/$task_base: commit $t_commit did not modify any declared files or tests ($NON_IGNORED_OWNED)"
                  fi
                fi
              fi
            fi
            ;;
        esac
        ;;
      deferred|skipped)
        expected_mark="-"
        TASK_DONE=$((TASK_DONE + 1))
        if [ "$t_def_by" != "user" ] || [ -z "$t_def_reason" ] || [ "$t_def_reason" = "null" ] || [ "$t_def_reason" = "~" ]; then
          append_violation "$scope_label/$task_base: state '$t_state' requires deferred_by: user and a non-empty deferred_reason"
        fi
        ;;
      in_progress)
        expected_mark="~"
        ;;
      blocked)
        expected_mark="!"
        ;;
      *)
        expected_mark=" "
        ;;
    esac

    SYNC_ERR="$(awk -v tbase="$task_base" -v tid="$t_id" -v tstem="$t_stem" -v want_mark="$expected_mark" -v tsha="$t_commit" -v scope="$scope_label" '
      NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
      in_fm && /^---[[:space:]]*$/ { in_fm = 0; next }
      in_fm { next }
      /^[[:space:]]*(```|~~~)/ { in_fence = !in_fence; next }
      in_fence { next }
      /^[[:space:]]*-[[:space:]]*\[[ xX~!>-]\]/ {
        line = $0
        if (index(line, "tasks/" tbase) > 0 || index(line, "(" tbase ")") > 0 || index(line, "] " tid " ") > 0 || index(line, "] " tid ":") > 0 || index(line, "] " tstem " ") > 0 || index(line, "] " tstem ":") > 0) {
          found = 1
          m = line
          sub(/^[[:space:]]*-[[:space:]]*\[/, "", m)
          mark = substr(m, 1, 1)
          if (mark == "X") mark = "x"
          if (mark != want_mark) {
            printf "%s: task %s has state marker [%s] in spec.md but expected [%s]", scope, tbase, mark, want_mark
            exit
          }
          if (want_mark == "x" && tsha != "" && tsha != "null" && match(line, /\[[0-9a-fA-F]{7,40}\]/)) {
            csha = substr(line, RSTART + 1, RLENGTH - 2)
            if (index(tsha, csha) != 1 && index(csha, tsha) != 1) {
              printf "MISMATCH:%s|%s", tsha, csha
              exit
            }
          }
          exit
        }
      }
      END {
        if (!found) {
          printf "%s: task worksheet %s is missing from owning spec.md checklist", scope, tbase
        }
      }
    ' "$owner_spec")"

    case "$SYNC_ERR" in
      MISMATCH:*)
        if [ "$SHA_TRACKING" = "strict" ]; then
          mm_rest="${SYNC_ERR#MISMATCH:}"
          mm_tsha="${mm_rest%%|*}"
          mm_csha="${mm_rest#*|}"
          mm_ok=0
          if [ "$HAS_GIT" = "1" ]; then
            if git -C "$PROJECT_DIR" cat-file -e "${mm_tsha}^{commit}" 2>/dev/null && git -C "$PROJECT_DIR" cat-file -e "${mm_csha}^{commit}" 2>/dev/null; then
              pid_t="$(git_patch_id_of_commit "$mm_tsha")"
              pid_c="$(git_patch_id_of_commit "$mm_csha")"
              if [ -n "$pid_t" ] && [ "$pid_t" = "$pid_c" ]; then
                mm_ok=1
              fi
            elif git -C "$PROJECT_DIR" merge-base --is-ancestor "$mm_tsha" HEAD 2>/dev/null && ! git -C "$PROJECT_DIR" merge-base --is-ancestor "$mm_csha" HEAD 2>/dev/null; then
              mm_ok=1
            elif git -C "$PROJECT_DIR" merge-base --is-ancestor "$mm_csha" HEAD 2>/dev/null && ! git -C "$PROJECT_DIR" merge-base --is-ancestor "$mm_tsha" HEAD 2>/dev/null; then
              mm_ok=1
            fi
          fi
          if [ "$mm_ok" = "0" ]; then
            append_violation "$scope_label: task $task_base commit $mm_tsha mismatches spec.md checklist SHA $mm_csha"
          fi
        fi
        ;;
      "")
        ;;
      *)
        append_violation "$SYNC_ERR"
        ;;
    esac
  done
}

git_patch_id_of_commit() {
  sha_arg="$1"
  git -C "$PROJECT_DIR" diff-tree --no-ext-diff -p --root "$sha_arg" 2>/dev/null | git patch-id --stable 2>/dev/null | awk 'NR == 1 { print $1; exit }'
}

commit_patch_in_history() {
  needle_sha="$1"
  haystack_rev="$2"
  needle_pid="$(git_patch_id_of_commit "$needle_sha")"
  [ -n "$needle_pid" ] || return 1
  git -C "$PROJECT_DIR" log -n 100 --no-ext-diff -p --root "$haystack_rev" 2>/dev/null | git patch-id --stable 2>/dev/null | awk -v npid="$needle_pid" '
    $1 == npid { found = 1; exit }
    END { exit (found ? 0 : 1) }
  '
}

verify_review_stamp() {
  rev_sha="$1"
  shas_list="$2"
  label="$3"

  if [ -z "$rev_sha" ] || [ "$rev_sha" = "null" ] || ! printf '%s\n' "$rev_sha" | grep -Eq '^[0-9a-fA-F]{7,40}$'; then
    append_violation "$label: missing hex last_reviewed_commit (sync present-tense docs and run Zero-Context Review before stopping)"
    return 0
  fi

  [ "$SHA_TRACKING" = "off" ] && return 0

  if [ "$HAS_GIT" = "1" ]; then
    if ! git -C "$PROJECT_DIR" cat-file -e "${rev_sha}^{commit}" 2>/dev/null; then
      return 0
    fi
    if [ "$SHA_TRACKING" = "advisory" ]; then
      return 0
    fi
    if ! git -C "$PROJECT_DIR" merge-base --is-ancestor "$rev_sha" HEAD 2>/dev/null; then
      return 0
    fi
    for t_sha in $shas_list; do
      if git -C "$PROJECT_DIR" cat-file -e "${t_sha}^{commit}" 2>/dev/null; then
        if ! git -C "$PROJECT_DIR" merge-base --is-ancestor "$t_sha" "$rev_sha" 2>/dev/null; then
          if ! commit_patch_in_history "$t_sha" "$rev_sha"; then
            append_violation "$label: task commit $t_sha is newer than last_reviewed_commit $rev_sha; re-run Zero-Context Review"
            return 0
          fi
        fi
      fi
    done
  fi
}

for root_spec in "$SPECS_DIR"/*/spec.md; do
  [ -f "$root_spec" ] || continue
  flow_dir="$(dirname "$root_spec")"
  flow_dir_name="$(basename "$flow_dir")"

  ROOT_META="$(awk '
    NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
    in_fm && /^---[[:space:]]*$/ { exit }
    in_fm && /^type:[[:space:]]*/ {
      v = $0; sub(/^type:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); tp = v
    }
    in_fm && /^flow_id:[[:space:]]*/ {
      v = $0; sub(/^flow_id:[[:space:]]*/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); fid = v
    }
    in_fm && /^state:[[:space:]]*/ {
      v = $0; sub(/^state:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); st = v
    }
    in_fm && /^has_chapters:[[:space:]]*/ {
      v = $0; sub(/^has_chapters:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); hc = v
    }
    in_fm && /^current_chapter:[[:space:]]*/ {
      v = $0; sub(/^current_chapter:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); cc = v
    }
    in_fm && /^last_reviewed_commit:[[:space:]]*/ {
      v = $0; sub(/^last_reviewed_commit:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); lrc = v
    }
    in_fm && /^gate:[[:space:]]*/ {
      v = $0; sub(/^gate:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); gt = tolower(v)
    }
    in_fm && /^paused:[[:space:]]*/ {
      v = $0; sub(/^paused:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); psd = tolower(v)
    }
    in_fm && /^handoff:[[:space:]]*/ {
      v = $0; sub(/^handoff:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); hnd = tolower(v)
    }
    END { printf "%s|%s|%s|%s|%s|%s|%s|%s|%s\n", tp, fid, st, hc, cc, lrc, gt, psd, hnd }
  ' "$root_spec")"

  r_type="${ROOT_META%%|*}"; rest0="${ROOT_META#*|}"
  r_fid="${rest0%%|*}"; rest1="${rest0#*|}"
  r_state="${rest1%%|*}"; rest2="${rest1#*|}"
  r_has_ch="${rest2%%|*}"; rest3="${rest2#*|}"
  r_curr_ch="${rest3%%|*}"; rest4="${rest3#*|}"
  r_rev_sha="${rest4%%|*}"; rest5="${rest4#*|}"
  r_gate="${rest5%%|*}"; rest6="${rest5#*|}"
  r_paused="${rest6%%|*}"; r_handoff="${rest6#*|}"
  [ -z "$r_fid" ] && r_fid="$flow_dir_name"

  [ "$r_state" = "archived" ] && continue
  [ "$r_type" = "flow" ] && continue
  [ "$r_gate" = "off" ] || [ "$r_gate" = "advisory" ] && continue
  [ "$r_state" = "paused" ] || [ "$r_paused" = "true" ] || [ "$r_handoff" = "true" ] && continue

  check_living_doc_hygiene "$root_spec" "specs/$flow_dir_name/spec.md" "0"

  if [ -d "$flow_dir/tasks" ]; then
    for tf in "$flow_dir/tasks"/*.md; do
      [ -f "$tf" ] || continue
      tb="$(basename "$tf")"
      if [ "$tb" = "index.md" ]; then
        check_living_doc_hygiene "$tf" "specs/$flow_dir_name/tasks/index.md" "1"
      else
        check_living_doc_hygiene "$tf" "specs/$flow_dir_name/tasks/$tb" "0"
      fi
    done
  fi

  if [ -d "$flow_dir/chapters" ] || [ "$r_has_ch" = "true" ]; then
    ch_index="$flow_dir/chapters/index.md"
    if [ ! -f "$ch_index" ]; then
      if [ "$IS_LEAF_SUBAGENT" = "0" ]; then
        append_violation "specs/$flow_dir_name/chapters/index.md: missing chapter catalog index.md"
      fi
    else
      check_living_doc_hygiene "$ch_index" "specs/$flow_dir_name/chapters/index.md" "1"
    fi

    CH_TOTAL=0
    CH_CLOSED=0
    CURR_CH_IS_COMPLETED=0
    CURR_CH_FOUND=0

    for ch_dir in "$flow_dir/chapters"/ch*; do
      [ -d "$ch_dir" ] || continue
      ch_id="$(basename "$ch_dir")"
      CH_TOTAL=$((CH_TOTAL + 1))
      ch_spec="$ch_dir/spec.md"
      if [ ! -f "$ch_spec" ]; then
        append_violation "specs/$flow_dir_name/chapters/$ch_id: missing spec.md"
        continue
      fi

      check_living_doc_hygiene "$ch_spec" "specs/$flow_dir_name/chapters/$ch_id/spec.md" "0"
      if [ -d "$ch_dir/tasks" ]; then
        for ctf in "$ch_dir/tasks"/*.md; do
          [ -f "$ctf" ] || continue
          ctb="$(basename "$ctf")"
          if [ "$ctb" = "index.md" ]; then
            check_living_doc_hygiene "$ctf" "specs/$flow_dir_name/chapters/$ch_id/tasks/index.md" "1"
          else
            check_living_doc_hygiene "$ctf" "specs/$flow_dir_name/chapters/$ch_id/tasks/$ctb" "0"
          fi
        done
      fi

      if [ "$IS_LEAF_SUBAGENT" = "0" ]; then
        if [ -f "$ch_index" ] && ! grep -Fq "$ch_id" "$ch_index"; then
          append_violation "specs/$flow_dir_name/chapters/index.md: missing entry for chapter $ch_id"
        fi
        if ! grep -Fq "$ch_id" "$root_spec"; then
          append_violation "specs/$flow_dir_name/spec.md: full-plan roadmap is missing chapter $ch_id"
        fi
      fi

      CH_META="$(awk '
        NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
        in_fm && /^---[[:space:]]*$/ { exit }
        in_fm && /^state:[[:space:]]*/ {
          v = $0; sub(/^state:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); st = v
        }
        in_fm && /^last_reviewed_commit:[[:space:]]*/ {
          v = $0; sub(/^last_reviewed_commit:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); lrc = v
        }
        in_fm && /^deferred_by:[[:space:]]*/ {
          v = $0; sub(/^deferred_by:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); dby = v
        }
        in_fm && /^deferred_reason:[[:space:]]*/ {
          v = $0; sub(/^deferred_reason:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); drsn = v
        }
        in_fm && /^paused:[[:space:]]*/ {
          v = $0; sub(/^paused:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); psd = tolower(v)
        }
        in_fm && /^handoff:[[:space:]]*/ {
          v = $0; sub(/^handoff:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); hnd = tolower(v)
        }
        END { printf "%s|%s|%s|%s|%s|%s\n", st, lrc, dby, drsn, psd, hnd }
      ' "$ch_spec")"
      c_state="${CH_META%%|*}"; c_r1="${CH_META#*|}"
      c_rev_sha="${c_r1%%|*}"; c_r2="${c_r1#*|}"
      c_def_by="${c_r2%%|*}"; c_r3="${c_r2#*|}"
      c_def_reason="${c_r3%%|*}"; c_r4="${c_r3#*|}"
      c_paused="${c_r4%%|*}"; c_handoff="${c_r4#*|}"

      if [ "$ch_id" = "$r_curr_ch" ]; then
        CURR_CH_FOUND=1
        if [ "$c_state" = "completed" ] || [ "$c_state" = "deferred" ] || [ "$c_state" = "skipped" ]; then
          CURR_CH_IS_COMPLETED=1
        fi
      fi

      if [ "$c_state" = "paused" ] || [ "$c_paused" = "true" ] || [ "$c_handoff" = "true" ]; then
        continue
      fi

      check_tasks_against_spec "$ch_spec" "$ch_dir/tasks" "specs/$flow_dir_name/chapters/$ch_id"

      if [ "$c_state" = "deferred" ] || [ "$c_state" = "skipped" ]; then
        if [ "$c_def_by" != "user" ] || [ -z "$c_def_reason" ] || [ "$c_def_reason" = "null" ] || [ "$c_def_reason" = "~" ]; then
          append_violation "specs/$flow_dir_name/chapters/$ch_id: state '$c_state' requires deferred_by: user and a non-empty deferred_reason"
        fi
        CH_CLOSED=$((CH_CLOSED + 1))
        continue
      fi

      NEED_CH_REVIEW=0
      if [ "$c_state" = "completed" ]; then
        if [ "$TASK_TOTAL" -eq 0 ] || [ "$TASK_DONE" -lt "$TASK_TOTAL" ]; then
          append_violation "specs/$flow_dir_name/chapters/$ch_id: chapter cannot be marked completed while $((TASK_TOTAL - TASK_DONE)) of $TASK_TOTAL task(s) remain incomplete (or 0 tasks exist)"
        fi
        CH_CLOSED=$((CH_CLOSED + 1))
        NEED_CH_REVIEW=1
      elif [ "$IS_LEAF_SUBAGENT" = "0" ] && [ "$TASK_TOTAL" -gt 0 ] && [ "$TASK_DONE" -eq "$TASK_TOTAL" ]; then
        if [ "$r_state" = "active" ] || [ "$r_state" = "completed" ] || [ "$c_state" = "active" ]; then
          append_violation "specs/$flow_dir_name/chapters/$ch_id: all $TASK_TOTAL task(s) are done, but chapter is not closed (sync present-tense docs/roadmap, run Zero-Context Review, and set state: completed)"
          NEED_CH_REVIEW=1
        fi
      fi

      if [ "$NEED_CH_REVIEW" = "1" ]; then
        verify_review_stamp "$c_rev_sha" "$COMPLETED_SHAS" "specs/$flow_dir_name/chapters/$ch_id"
        if [ "$IS_LEAF_SUBAGENT" = "0" ] && [ "$c_state" = "completed" ]; then
          ROOT_CH_CHECK="$(awk -v cid="$ch_id" '
            NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
            in_fm && /^---[[:space:]]*$/ { in_fm = 0; next }
            in_fm { next }
            /^[[:space:]]*-[[:space:]]*\[[xX]\]/ {
              if (index($0, cid) > 0) { found = 1; exit }
            }
            END { print (found ? "1" : "0") }
          ' "$root_spec")"
          if [ "$ROOT_CH_CHECK" = "0" ]; then
            append_violation "specs/$flow_dir_name/spec.md: completed chapter $ch_id must be marked [x] in root Implementation Plan"
          fi
        fi
      fi
    done

    if [ "$r_state" = "completed" ] && { [ "$CH_TOTAL" -eq 0 ] || [ "$CH_CLOSED" -lt "$CH_TOTAL" ]; }; then
      append_violation "specs/$flow_dir_name/spec.md: flow cannot be marked completed while $((CH_TOTAL - CH_CLOSED)) of $CH_TOTAL chapter(s) remain open (anti-skip guard)"
    fi

    if [ "$IS_LEAF_SUBAGENT" = "0" ] && [ "$CH_TOTAL" -gt 0 ]; then
      if [ "$CH_CLOSED" -lt "$CH_TOTAL" ]; then
        if [ "$r_state" != "completed" ] && { [ -z "$r_curr_ch" ] || [ "$r_curr_ch" = "null" ] || [ "$CURR_CH_FOUND" = "0" ] || [ "$CURR_CH_IS_COMPLETED" = "1" ]; }; then
          append_violation "specs/$flow_dir_name/spec.md: current_chapter '$r_curr_ch' must advance to an open remaining chapter"
        fi
      elif [ "$r_state" = "completed" ]; then
        verify_review_stamp "$r_rev_sha" "" "specs/$flow_dir_name/spec.md"
      fi
    fi
  else
    check_tasks_against_spec "$root_spec" "$flow_dir/tasks" "specs/$flow_dir_name"
    if [ "$r_state" = "completed" ]; then
      if [ "$TASK_TOTAL" -eq 0 ] || [ "$TASK_DONE" -lt "$TASK_TOTAL" ]; then
        append_violation "specs/$flow_dir_name/spec.md: single-chapter flow cannot be marked completed while $((TASK_TOTAL - TASK_DONE)) of $TASK_TOTAL task(s) remain incomplete (or 0 tasks exist)"
      fi
      verify_review_stamp "$r_rev_sha" "$COMPLETED_SHAS" "specs/$flow_dir_name/spec.md"
    elif [ "$IS_LEAF_SUBAGENT" = "0" ] && [ "$r_state" = "active" ] && [ "$TASK_TOTAL" -gt 0 ] && [ "$TASK_DONE" -eq "$TASK_TOTAL" ]; then
      verify_review_stamp "$r_rev_sha" "$COMPLETED_SHAS" "specs/$flow_dir_name/spec.md"
    fi
  fi
done

if [ -z "$VIOLATIONS" ]; then
  emit_allow
fi

REASON="Flow Stop Gate blocked turn completion — synchronize present-tense Markdown and complete Zero-Context Chapter Review before stopping: $VIOLATIONS"
ESCAPED_REASON="$(printf '%s' "$REASON" | awk '
  BEGIN { ORS = "" }
  {
    gsub(/\\/, "\\\\")
    gsub(/"/, "\\\"")
    gsub(/\r/, "")
    gsub(/\t/, " ")
    if (NR > 1) printf "\\n"
    printf "%s", $0
  }
')"

case "$HARNESS" in
  agy|antigravity)
    printf '{"decision":"continue","reason":"%s"}\n' "$ESCAPED_REASON"
    ;;
  cursor)
    printf '{"followup_message":"%s"}\n' "$ESCAPED_REASON"
    ;;
  json)
    printf '{"blocked":true,"reason":"%s"}\n' "$ESCAPED_REASON"
    ;;
  claude|vscode|*)
    printf '{"decision":"block","reason":"%s"}\n' "$ESCAPED_REASON"
    ;;
esac
