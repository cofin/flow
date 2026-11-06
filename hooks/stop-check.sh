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

STDIN_PAYLOAD=""
if [ ! -t 0 ]; then
  STDIN_PAYLOAD="$(cat || true)"
fi

IS_LEAF_SUBAGENT=0
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
      if (match(buf, /"lastUserInput"[[:space:]]*:[[:space:]]*"[^"]*(agents\/(executor|researcher|code-reviewer|quality-reviewer|plan-generator)\.md|\.agents\/agents\/)/)) {
        leaf = 1
      }

      printf "%d|%d|%s\n", bypass, leaf, proj
    }
  ')"

  BYPASS_FLAG="${PARSED_STDIN%%|*}"
  REST_STDIN="${PARSED_STDIN#*|}"
  IS_LEAF_SUBAGENT="${REST_STDIN%%|*}"
  DETECTED_PROJ="${REST_STDIN#*|}"

  if [ "$BYPASS_FLAG" = "1" ]; then
    emit_allow
  fi
  if [ -z "$PROJECT_DIR" ] && [ -n "$DETECTED_PROJ" ]; then
    PROJECT_DIR="$DETECTED_PROJ"
  fi
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

SPECS_DIR="$PROJECT_DIR/$BUNDLE_REL/specs"
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
  DOC_ERR="$(awk -v rel="$rel_label" -v is_idx="$is_index_file" '
    NR == 1 && /^---[[:space:]]*$/ {
      if (is_idx == "1") {
        printf "%s: subdirectory index.md must not contain YAML frontmatter", rel
        exit
      }
      in_fm = 1
      next
    }
    in_fm && /^---[[:space:]]*$/ {
      in_fm = 0
      next
    }
    in_fm { next }
    /^[[:space:]]*(```|~~~)/ {
      in_fence = !in_fence
      next
    }
    in_fence { next }
    /^[[:space:]]*---[[:space:]]*$/ {
      printf "%s: standalone --- horizontal rule forbidden in bundle Markdown body", rel
      exit
    }
    tolower($0) ~ /^[[:space:]]*#+[[:space:]]*(revision history|change history|changelog|decision history)([[:space:]:]|$)/ {
      printf "%s: historical changelog/revision section forbidden in present-tense living spec", rel
      exit
    }
    /^[[:space:]]*-[[:space:]]*\[[^]]*\][[:space:]]*~~/ {
      printf "%s: struck-through obsolete checklist item forbidden; rewrite in place in present tense", rel
      exit
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
      NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
      in_fm && /^---[[:space:]]*$/ { exit }
      in_fm && /^id:[[:space:]]*/ {
        v = $0; sub(/^id:[[:space:]]*/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); id = v
      }
      in_fm && /^state:[[:space:]]*/ {
        v = $0; sub(/^state:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); st = v
      }
      in_fm && /^commit:[[:space:]]*/ {
        v = $0; sub(/^commit:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); cm = v
      }
      END { printf "%s|%s|%s\n", id, st, cm }
    ' "$task_file")"

    t_id="${TASK_META%%|*}"
    t_rest="${TASK_META#*|}"
    t_state="${t_rest%%|*}"
    t_commit="${t_rest#*|}"
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
            fi
            ;;
        esac
        ;;
      deferred|skipped)
        expected_mark="-"
        TASK_DONE=$((TASK_DONE + 1))
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
              printf "%s: task %s commit %s mismatches spec.md checklist SHA %s", scope, tbase, tsha, csha
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

    if [ -n "$SYNC_ERR" ]; then
      append_violation "$SYNC_ERR"
    fi
  done
}

verify_review_stamp() {
  rev_sha="$1"
  shas_list="$2"
  label="$3"

  if [ -z "$rev_sha" ] || [ "$rev_sha" = "null" ] || ! printf '%s\n' "$rev_sha" | grep -Eq '^[0-9a-fA-F]{7,40}$'; then
    append_violation "$label: missing hex last_reviewed_commit (sync present-tense docs and run Zero-Context Review before stopping)"
    return 0
  fi

  if [ "$HAS_GIT" = "1" ]; then
    if ! git -C "$PROJECT_DIR" cat-file -e "${rev_sha}^{commit}" 2>/dev/null; then
      append_violation "$label: last_reviewed_commit '$rev_sha' does not exist in Git history"
      return 0
    fi
    for t_sha in $shas_list; do
      if git -C "$PROJECT_DIR" cat-file -e "${t_sha}^{commit}" 2>/dev/null; then
        if ! git -C "$PROJECT_DIR" merge-base --is-ancestor "$t_sha" "$rev_sha" 2>/dev/null; then
          append_violation "$label: task commit $t_sha is newer than last_reviewed_commit $rev_sha; re-run Zero-Context Review"
          return 0
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
    END { printf "%s|%s|%s|%s|%s|%s\n", tp, fid, st, hc, cc, lrc }
  ' "$root_spec")"

  r_type="${ROOT_META%%|*}"; rest0="${ROOT_META#*|}"
  r_fid="${rest0%%|*}"; rest1="${rest0#*|}"
  r_state="${rest1%%|*}"; rest2="${rest1#*|}"
  r_has_ch="${rest2%%|*}"; rest3="${rest2#*|}"
  r_curr_ch="${rest3%%|*}"; r_rev_sha="${rest3#*|}"
  [ -z "$r_fid" ] && r_fid="$flow_dir_name"

  [ "$r_state" = "archived" ] && continue
  [ "$r_type" = "flow" ] && continue

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
        END { printf "%s|%s\n", st, lrc }
      ' "$ch_spec")"
      c_state="${CH_META%%|*}"
      c_rev_sha="${CH_META#*|}"

      if [ "$ch_id" = "$r_curr_ch" ]; then
        CURR_CH_FOUND=1
        if [ "$c_state" = "completed" ] || [ "$c_state" = "deferred" ] || [ "$c_state" = "skipped" ]; then
          CURR_CH_IS_COMPLETED=1
        fi
      fi

      check_tasks_against_spec "$ch_spec" "$ch_dir/tasks" "specs/$flow_dir_name/chapters/$ch_id"

      if [ "$c_state" = "deferred" ] || [ "$c_state" = "skipped" ]; then
        CH_CLOSED=$((CH_CLOSED + 1))
        continue
      fi

      NEED_CH_REVIEW=0
      if [ "$c_state" = "completed" ]; then
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

    if [ "$IS_LEAF_SUBAGENT" = "0" ] && [ "$CH_TOTAL" -gt 0 ]; then
      if [ "$CH_CLOSED" -lt "$CH_TOTAL" ]; then
        if [ -z "$r_curr_ch" ] || [ "$r_curr_ch" = "null" ] || [ "$CURR_CH_FOUND" = "0" ] || [ "$CURR_CH_IS_COMPLETED" = "1" ]; then
          append_violation "specs/$flow_dir_name/spec.md: current_chapter '$r_curr_ch' must advance to an open remaining chapter"
        fi
      elif [ "$r_state" = "completed" ]; then
        verify_review_stamp "$r_rev_sha" "" "specs/$flow_dir_name/spec.md"
      fi
    fi
  else
    check_tasks_against_spec "$root_spec" "$flow_dir/tasks" "specs/$flow_dir_name"
    if [ "$r_state" = "completed" ]; then
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
