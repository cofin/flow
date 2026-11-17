#!/usr/bin/env sh
# Portable POSIX sh + awk PreToolUse safety guard for Flow.
# Enforces Git tag non-mutation, prompts on force-push/hard-reset, guards read-only agents,
# and applies Claude-only (CLAUDECODE=1, non-Codex) Agent tier fallback when the Claude Mod is unloaded.
set -eu

HOOK_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd || dirname -- "$0")"
. "$HOOK_DIR/lib/common.sh"

flow_parse_args "claude" "$@"

if [ "$HARNESS" = "claude" ] && [ -n "${CURSOR_VERSION:-}" ]; then
  printf '{}\n'
  exit 0
fi

flow_read_stdin

PARSED="$(printf '%s\n' "$STDIN_PAYLOAD" | awk '
  function unescape_json(raw,   i, n, ch, nxt, out) {
    out = ""
    n = length(raw)
    for (i = 1; i <= n; i++) {
      ch = substr(raw, i, 1)
      if (ch == "\\" && i < n) {
        nxt = substr(raw, i + 1, 1)
        if (nxt == "\\") { out = out "\\"; i++; continue }
        if (nxt == "/") { out = out "/"; i++; continue }
        if (nxt == "\"") { out = out "\""; i++; continue }
        if (nxt == "n") { out = out "\n"; i++; continue }
        if (nxt == "t") { out = out " "; i++; continue }
        if (nxt == "r") { i++; continue }
      }
      out = out ch
    }
    return out
  }
  { buf = buf " " $0 }
  END {
    tool_name = ""
    cmd_line = ""
    agent_id = ""
    proj = ""
    payload_cwd = ""
    target_path = ""

    if (match(buf, /"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"workspacePaths"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
      sub(/"$/, "", s); gsub(/\\\\/, "/", s); proj = s
    } else if (match(buf, /"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"workspace_roots"[[:space:]]*:[[:space:]]*\[[[:space:]]*"/, "", s)
      sub(/"$/, "", s); gsub(/\\\\/, "/", s); proj = s
    } else if (match(buf, /"cwd"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"cwd"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s); gsub(/\\\\/, "/", s); proj = s
    } else if (match(buf, /"workspaceRoot"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"workspaceRoot"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s); gsub(/\\\\/, "/", s); proj = s
    }

    if (match(buf, /"cwd"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"cwd"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s); gsub(/\\\\/, "/", s); payload_cwd = s
    }

    if (match(buf, /"toolCall"[[:space:]]*:[[:space:]]*\{[[:space:]]*"name"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"name"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      tool_name = s
    } else if (match(buf, /"tool_name"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"tool_name"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      tool_name = s
    }

    if (match(buf, /"CommandLine"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"CommandLine"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      cmd_line = unescape_json(s)
    } else if (match(buf, /"command"[[:space:]]*:[[:space:]]*"([^"\\]|\\.)*"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"command"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      cmd_line = unescape_json(s)
    }

    if (match(buf, /"TargetPath"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"TargetPath"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); target_path = s
    } else if (match(buf, /"Path"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"Path"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); target_path = s
    } else if (match(buf, /"file_path"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"file_path"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); target_path = s
    } else if (match(buf, /"TargetFile"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH); sub(/^.*"TargetFile"[[:space:]]*:[[:space:]]*"/, "", s); sub(/"$/, "", s); gsub(/\\\\/, "/", s); target_path = s
    }

    if (match(buf, /"agentName"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"agentName"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      agent_id = s
    } else if (match(buf, /"agent_type"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"agent_type"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      agent_id = s
    } else if (match(buf, /"subagent_type"[[:space:]]*:[[:space:]]*"[^"]+"/)) {
      s = substr(buf, RSTART, RLENGTH)
      sub(/^.*"subagent_type"[[:space:]]*:[[:space:]]*"/, "", s)
      sub(/"$/, "", s)
      agent_id = s
    }

    gsub(/\|/, " ", tool_name)
    gsub(/\|/, " ", agent_id)
    gsub(/\|/, " ", proj)
    gsub(/\|/, " ", payload_cwd)
    gsub(/\|/, " ", target_path)
    printf "%s|%s|%s|%s|%s|%s\n", tool_name, agent_id, proj, payload_cwd, target_path, cmd_line
  }
')"

TOOL_NAME="${PARSED%%|*}"; R_1="${PARSED#*|}"
AGENT_ID="${R_1%%|*}"; R_2="${R_1#*|}"
DETECTED_PROJ="${R_2%%|*}"; R_3="${R_2#*|}"
PAYLOAD_CWD="${R_3%%|*}"; R_4="${R_3#*|}"
TARGET_PATH="${R_4%%|*}"; CMD_LINE="${R_4#*|}"

if [ -z "$PROJECT_DIR" ]; then
  if [ -n "$DETECTED_PROJ" ]; then
    PROJECT_DIR="$DETECTED_PROJ"
  elif [ -n "${CURSOR_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CURSOR_PROJECT_DIR"
  elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
    PROJECT_DIR="$CLAUDE_PROJECT_DIR"
  else
    PROJECT_DIR="$(pwd)"
  fi
fi

BASE_DIR="${PAYLOAD_CWD:-$PROJECT_DIR}"

resolve_dir() {
  raw_d="$1"
  rel_base="$2"
  raw_d="$(printf '%s' "$raw_d" | tr '\\' '/')"
  while [ "$raw_d" != "/" ] && [ "${raw_d%/}" != "$raw_d" ]; do
    case "$raw_d" in
      [A-Za-z]:/) break ;;
    esac
    raw_d="${raw_d%/}"
  done
  case "$raw_d" in
    ""|".")
      printf '%s\n' "$rel_base"
      return 0
      ;;
  esac
  case "$raw_d" in
    /*|[A-Za-z]:/*|[A-Za-z]:)
      joined="$raw_d"
      ;;
    *)
      if [ "$rel_base" = "/" ]; then
        joined="/$raw_d"
      elif [ -n "$rel_base" ]; then
        joined="${rel_base%/}/$raw_d"
      else
        joined="$raw_d"
      fi
      ;;
  esac
  if [ -d "$joined" ]; then
    (CDPATH= cd -- "$joined" 2>/dev/null && pwd) || printf '%s\n' "$joined"
  else
    printf '%s\n' "$joined"
  fi
}

is_incomplete_flow_spec() {
  fid="$1"
  raw_target_dir="${2:-}"
  [ -n "$fid" ] || return 1
  if [ -z "$raw_target_dir" ]; then
    raw_target_dir="$BASE_DIR"
  fi
  target_dir="$(resolve_dir "$raw_target_dir" "$BASE_DIR")"
  spec_root="$target_dir/.agents/bundles/specs/$fid"
  if [ ! -f "$spec_root/spec.md" ] && [ ! -d "$target_dir/.agents" ] && [ -f "$target_dir/.git" ] && command -v git >/dev/null 2>&1; then
    gcom="$(git -C "$target_dir" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
    if [ -n "$gcom" ]; then
      cmain="$(CDPATH= cd -- "$gcom/.." 2>/dev/null && pwd || true)"
      if [ -n "$cmain" ] && [ -f "$cmain/.agents/bundles/specs/$fid/spec.md" ]; then
        spec_root="$cmain/.agents/bundles/specs/$fid"
      fi
    fi
  fi
  [ -f "$spec_root/spec.md" ] || return 1

  R_META="$(awk '
    NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
    in_fm && /^---[[:space:]]*$/ { exit }
    in_fm && /^state:[[:space:]]*/ { v = $0; sub(/^state:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); st = v }
    in_fm && /^last_reviewed_commit:[[:space:]]*/ { v = $0; sub(/^last_reviewed_commit:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); lrc = v }
    END { printf "%s|%s\n", st, lrc }
  ' "$spec_root/spec.md")"
  rst="${R_META%%|*}"
  rlrc="${R_META#*|}"
  if [ "$rst" != "completed" ] || [ -z "$rlrc" ] || [ "$rlrc" = "null" ]; then
    return 0
  fi
  if [ -d "$spec_root/chapters" ]; then
    for chd in "$spec_root/chapters"/ch*; do
      [ -d "$chd" ] || continue
      [ -f "$chd/spec.md" ] || return 0
      cst="$(awk '
        NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
        in_fm && /^---[[:space:]]*$/ { exit }
        in_fm && /^state:[[:space:]]*/ { v = $0; sub(/^state:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); print v; exit }
      ' "$chd/spec.md")"
      case "$cst" in
        completed|deferred|skipped) ;;
        *) return 0 ;;
      esac
    done
  fi
  for tkf in "$spec_root"/tasks/*.md "$spec_root"/chapters/ch*/tasks/*.md; do
    [ -f "$tkf" ] || continue
    [ "$(basename "$tkf")" = "index.md" ] && continue
    tst="$(awk '
      NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
      in_fm && /^---[[:space:]]*$/ { exit }
      in_fm && /^state:[[:space:]]*/ { v = $0; sub(/^state:[[:space:]]*/, "", v); sub(/[[:space:]]+#.*$/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); print v; exit }
    ' "$tkf")"
    case "$tst" in
      completed|closed|deferred|skipped) ;;
      *) return 0 ;;
    esac
  done
  return 1
}

DECISION="allow"
REASON=""

case "$AGENT_ID" in
  code-reviewer|quality-reviewer|researcher|*:code-reviewer|*:quality-reviewer|*:researcher)
    case "$TOOL_NAME" in
      write_file|write_to_file|edit_file|replace_file_content|multi_replace_file_content|delete_file|notebook_edit|Write|Edit|MultiEdit|NotebookEdit)
        DECISION="deny"
        REASON="Flow safety guard: read-only agent '${AGENT_ID}' is forbidden from mutating repository files."
        ;;
    esac
    ;;
esac

if [ "$DECISION" = "allow" ] && [ "$TOOL_NAME" = "delete_file" ] && [ -n "$TARGET_PATH" ]; then
  DEL_TARGET="$(printf '%s\n' "$TARGET_PATH" | awk '
    {
      p = $0
      gsub(/\\/, "/", p)
      if (match(p, /\.agents\/bundles\/specs\/[A-Za-z0-9_-]+(\/spec\.md|\/)?$/)) {
        if (RSTART == 1 || substr(p, RSTART - 1, 1) == "/") {
          pref = (RSTART > 1) ? substr(p, 1, RSTART - 1) : ""
          while (length(pref) > 1 && !(pref ~ /^[A-Za-z]:\/$/) && substr(pref, length(pref), 1) == "/") {
            pref = substr(pref, 1, length(pref) - 1)
          }
          rest = substr(p, RSTART)
          sub(/^\.agents\/bundles\/specs\//, "", rest)
          sub(/\/.*$/, "", rest)
          printf "%s|%s\n", rest, pref
        }
      }
    }
  ')"
  if [ -n "$DEL_TARGET" ]; then
    DEL_FID="${DEL_TARGET%%|*}"
    DEL_DIR="${DEL_TARGET#*|}"
    if is_incomplete_flow_spec "$DEL_FID" "$DEL_DIR"; then
      DECISION="deny"
      REASON="Flow safety guard: cannot delete or archive specs/${DEL_FID} while chapters or tasks remain incomplete or unreviewed."
    fi
  fi
fi

if [ "$DECISION" = "allow" ] && [ -n "$CMD_LINE" ]; then
  case "$CMD_LINE" in
    *specs*)
      RM_TARGETS="$(printf '%s\n' "$CMD_LINE" | awk '
        function trim_str(s) {
          sub(/^[ \t\r\n]+/, "", s)
          sub(/[ \t\r\n]+$/, "", s)
          return s
        }
        function norm_slashes(s) {
          gsub(/\\/, "/", s)
          return s
        }
        function strip_trailing_slash(s) {
          while (length(s) > 1 && !(s ~ /^[A-Za-z]:\/$/) && substr(s, length(s), 1) == "/") {
            s = substr(s, 1, length(s) - 1)
          }
          return s
        }
        function is_abs_path(s) {
          return (substr(s, 1, 1) == "/" || s ~ /^[A-Za-z]:\// || s ~ /^[A-Za-z]:$/ || substr(s, 1, 1) == "~")
        }
        function combine_path(base, sub_p,   b, p) {
          p = strip_trailing_slash(norm_slashes(sub_p))
          if (p == "" || p == ".") return base
          if (is_abs_path(p) || base == "") return p
          b = strip_trailing_slash(norm_slashes(base))
          if (b == "/" || b ~ /^[A-Za-z]:\/$/) return b p
          return b "/" p
        }
        function split_segments(cmd, segs,   i, n, ch, in_sq, in_dq, paren_depth, cur, cnt, k, j, rest_s) {
          for (k in segs) delete segs[k]
          cnt = 0
          in_sq = 0
          in_dq = 0
          paren_depth = 0
          cur = ""
          n = length(cmd)
          for (i = 1; i <= n; i++) {
            ch = substr(cmd, i, 1)
            if (ch == "'"'"'" && !in_dq) {
              in_sq = !in_sq
              cur = cur ch
              continue
            }
            if (ch == "\"" && !in_sq) {
              if (i > 1 && substr(cmd, i - 1, 1) == "\\") {
                cur = cur ch
                continue
              }
              in_dq = !in_dq
              cur = cur ch
              continue
            }
            if (!in_sq && !in_dq) {
              if (ch == "(" && trim_str(cur) == "") {
                paren_depth++
                continue
              }
              if (ch == ")" && paren_depth > 0) {
                rest_s = substr(cmd, i + 1)
                if (rest_s ~ /^[ \t\r]*([;&|\n)]|$)/) {
                  paren_depth--
                  continue
                }
              }
              if (ch == "&" && i > 1 && substr(cmd, i - 1, 1) == ">") {
                cur = cur ch
                continue
              }
              if (ch == ";" || ch == "|" || ch == "&" || ch == "\n") {
                cur = trim_str(cur)
                if (cur != "") {
                  cnt++
                  segs[cnt] = cur
                }
                cur = ""
                continue
              }
            }
            cur = cur ch
          }
          cur = trim_str(cur)
          if (cur != "") {
            cnt++
            segs[cnt] = cur
          }
          return cnt
        }
        function tokenize_seg(seg, toks,   i, n, ch, nxt, in_sq, in_dq, tok, has_tok, cnt, k) {
          for (k in toks) delete toks[k]
          cnt = 0
          in_sq = 0
          in_dq = 0
          tok = ""
          has_tok = 0
          n = length(seg)
          for (i = 1; i <= n; i++) {
            ch = substr(seg, i, 1)
            if (in_sq) {
              if (ch == "'"'"'") {
                in_sq = 0
              } else {
                tok = tok ch
              }
              continue
            }
            if (in_dq) {
              if (ch == "\"") {
                in_dq = 0
              } else if (ch == "\\" && i < n) {
                nxt = substr(seg, i + 1, 1)
                if (nxt == "\"" || nxt == "\\") {
                  tok = tok nxt
                  i++
                } else {
                  tok = tok ch
                }
              } else {
                tok = tok ch
              }
              continue
            }
            if (ch == " " || ch == "\t" || ch == "\r" || ch == "\n") {
              if (has_tok) {
                cnt++
                toks[cnt] = tok
                tok = ""
                has_tok = 0
              }
              continue
            }
            if (ch == "'"'"'") {
              in_sq = 1
              has_tok = 1
              continue
            }
            if (ch == "\"") {
              in_dq = 1
              has_tok = 1
              continue
            }
            if (ch == "\\" && i < n) {
              nxt = substr(seg, i + 1, 1)
              if (nxt == " " || nxt == "\t" || nxt == "\"" || nxt == "'"'"'") {
                tok = tok nxt
                has_tok = 1
                i++
                continue
              }
            }
            tok = tok ch
            has_tok = 1
          }
          if (has_tok) {
            cnt++
            toks[cnt] = tok
          }
          return cnt
        }
        function expand_braces(tok, is_ps_del, out_paths,   queue, qhead, qtail, cur, pre, inside, post, nopts, opts, o, out_cnt, k, split_n, c_arr, ci) {
          for (k in out_paths) delete out_paths[k]
          queue[1] = norm_slashes(tok)
          qhead = 1
          qtail = 1
          out_cnt = 0
          while (qhead <= qtail) {
            cur = queue[qhead]
            qhead++
            if (match(cur, /\{[^{}]*,[^{}]*\}/) && qtail < 64) {
              pre = substr(cur, 1, RSTART - 1)
              inside = substr(cur, RSTART + 1, RLENGTH - 2)
              post = substr(cur, RSTART + RLENGTH)
              nopts = split(inside, opts, ",")
              for (o = 1; o <= nopts; o++) {
                if (qtail >= 64) break
                qtail++
                queue[qtail] = pre opts[o] post
              }
            } else if (is_ps_del && index(cur, ",") > 0) {
              split_n = split(cur, c_arr, ",")
              for (ci = 1; ci <= split_n; ci++) {
                if (c_arr[ci] != "") {
                  out_cnt++
                  out_paths[out_cnt] = c_arr[ci]
                }
              }
            } else {
              out_cnt++
              out_paths[out_cnt] = cur
            }
          }
          return out_cnt
        }
        {
          buf = (NR == 1 ? $0 : buf "\n" $0)
        }
        END {
          qhead = 1
          qtail = 1
          work_cmd[1] = buf
          work_dir[1] = ""
          while (qhead <= qtail) {
            wcmd = work_cmd[qhead]
            cur_dir = work_dir[qhead]
            qhead++
            nseg = split_segments(wcmd, segs)
            for (si = 1; si <= nseg; si++) {
              nt = tokenize_seg(segs[si], toks)
              if (nt == 0) continue
              cmd_idx = 1
              while (cmd_idx <= nt) {
                t_cand = toks[cmd_idx]
                if (t_cand ~ /^[A-Za-z_][A-Za-z0-9_]*=.*/ || t_cand == "command" || t_cand == "env" || t_cand == "sudo") {
                  cmd_idx++
                  continue
                }
                break
              }
              if (cmd_idx > nt) continue
              cmd_base = norm_slashes(toks[cmd_idx])
              sub(/^.*\//, "", cmd_base)
              cmd_lc = tolower(cmd_base)

              if (cmd_lc == "sh" || cmd_lc == "bash" || cmd_lc == "zsh" || cmd_lc == "dash" || cmd_lc == "ksh" || cmd_lc == "pwsh" || cmd_lc == "powershell") {
                for (ki = cmd_idx + 1; ki < nt; ki++) {
                  klc = tolower(toks[ki])
                  if ((klc == "-c" || klc == "-command" || klc == "-lc") && qtail < 16) {
                    qtail++
                    work_cmd[qtail] = toks[ki + 1]
                    work_dir[qtail] = cur_dir
                    break
                  }
                }
                continue
              }

              if (cmd_lc == "cd" || cmd_lc == "pushd" || cmd_lc == "set-location" || cmd_lc == "sl") {
                for (ki = cmd_idx + 1; ki <= nt; ki++) {
                  klc = tolower(toks[ki])
                  if (toks[ki] == "--" && ki + 1 <= nt) {
                    cur_dir = combine_path(cur_dir, toks[ki + 1])
                    break
                  }
                  if ((cmd_lc == "set-location" || cmd_lc == "sl") && klc == "-stackname") {
                    ki++
                    continue
                  }
                  if ((cmd_lc == "set-location" || cmd_lc == "sl") && klc ~ /^-path=.+$/) {
                    cur_dir = combine_path(cur_dir, substr(toks[ki], 7))
                    break
                  }
                  if ((cmd_lc == "set-location" || cmd_lc == "sl") && klc ~ /^-literalpath=.+$/) {
                    cur_dir = combine_path(cur_dir, substr(toks[ki], 14))
                    break
                  }
                  if (toks[ki] ~ /^-/) continue
                  cur_dir = combine_path(cur_dir, toks[ki])
                  break
                }
                continue
              }

              is_del = 0
              is_ps_del = 0
              arg_start = cmd_idx + 1
              seg_dir = cur_dir
              if (cmd_lc == "rm" || cmd_lc == "rmdir") {
                is_del = 1
              } else if (cmd_lc == "remove-item" || cmd_lc == "ri" || cmd_lc == "del" || cmd_lc == "rd") {
                is_del = 1
                is_ps_del = 1
              } else if (cmd_lc == "git") {
                for (ki = cmd_idx + 1; ki <= nt; ki++) {
                  gt = toks[ki]
                  if (gt == "-C" && ki + 1 <= nt) {
                    seg_dir = combine_path(seg_dir, toks[ki + 1])
                    ki++
                  } else if (gt ~ /^-C.+$/) {
                    seg_dir = combine_path(seg_dir, substr(gt, 3))
                  } else if (gt == "--work-tree" && ki + 1 <= nt) {
                    seg_dir = combine_path(seg_dir, toks[ki + 1])
                    ki++
                  } else if (gt ~ /^--work-tree=.+$/) {
                    seg_dir = combine_path(seg_dir, substr(gt, 13))
                  } else if (gt == "-c" || gt == "--git-dir" || gt == "--namespace" || gt == "--super-prefix" || gt == "--config-env") {
                    ki++
                  } else if (gt ~ /^-/) {
                    continue
                  } else {
                    if (tolower(gt) == "rm") {
                      is_del = 1
                      arg_start = ki + 1
                    }
                    break
                  }
                }
              }

              if (!is_del) continue
              for (ai = arg_start; ai <= nt; ai++) {
                at = toks[ai]
                if (is_ps_del) {
                  alc = tolower(at)
                  if (alc ~ /^-path=.+$/) at = substr(at, 7)
                  else if (alc ~ /^-literalpath=.+$/) at = substr(at, 14)
                }
                if (at ~ /^-/) continue
                nc = expand_braces(at, is_ps_del, cands)
                for (ci = 1; ci <= nc; ci++) {
                  cand = cands[ci]
                  if (match(cand, /\.agents\/bundles\/specs\/[A-Za-z0-9_-]+(\/spec\.md|\/)?$/)) {
                    if (RSTART == 1 || substr(cand, RSTART - 1, 1) == "/") {
                      pref = (RSTART > 1) ? substr(cand, 1, RSTART - 1) : ""
                      pref = strip_trailing_slash(pref)
                      rest = substr(cand, RSTART)
                      sub(/^\.agents\/bundles\/specs\//, "", rest)
                      sub(/\/.*$/, "", rest)
                      target_root = (pref != "") ? combine_path(seg_dir, pref) : seg_dir
                      printf "%s|%s\n", rest, target_root
                    }
                  }
                }
              }
            }
          }
        }
      ')"
      if [ -n "$RM_TARGETS" ]; then
        while IFS= read -r entry; do
          [ -n "$entry" ] || continue
          rm_fid="${entry%%|*}"
          rm_dir="${entry#*|}"
          if is_incomplete_flow_spec "$rm_fid" "$rm_dir"; then
            DECISION="deny"
            REASON="Flow safety guard: cannot delete or archive specs/${rm_fid} while chapters or tasks remain incomplete or unreviewed."
            break
          fi
        done <<EOF
$RM_TARGETS
EOF
      fi
      ;;
  esac
fi

if [ "$DECISION" = "allow" ] && [ -n "$CMD_LINE" ]; then
  GIT_VERDICT="$(printf '%s\n' "$CMD_LINE" | awk '
    {
      c = $0
      if (match(c, /(^|[;&|[:space:]])git[[:space:]]+push([[:space:]]+[^;&|]*)?[[:space:]]+--tags([[:space:]];|&|$)/)) {
        print "deny|Flow safety guard: creating, deleting, or pushing Git tags is forbidden by Flow discipline."
        exit
      }
      if (match(c, /(^|[;&|[:space:]])git[[:space:]]+tag([[:space:]]+|$)/)) {
        tail = substr(c, RSTART)
        sub(/^[;&|[:space:]]*git[[:space:]]+tag[[:space:]]*/, "", tail)
        sub(/[;&|].*$/, "", tail)
        gsub(/[[:space:]]+$/, "", tail)
        if (tail == "" || tail ~ /^(-l|--list|--contains|--points-at|-v|--verify)([[:space:]]|$)/) {
          print "allow|"
          exit
        }
        print "deny|Flow safety guard: creating, deleting, or pushing Git tags is forbidden by Flow discipline."
        exit
      }
      if (match(c, /(^|[;&|[:space:]])git[[:space:]]+push([[:space:]]+[^;&|]*)?[[:space:]]+(-f|--force|--force-with-lease)([[:space:];&|]|$)/)) {
        print "ask|Flow safety guard: destructive Git force-push requires explicit user confirmation."
        exit
      }
      if (match(c, /(^|[;&|[:space:]])git[[:space:]]+reset[[:space:]]+--hard([[:space:];&|]|$)/)) {
        print "ask|Flow safety guard: destructive git reset --hard requires explicit user confirmation."
        exit
      }
      print "allow|"
    }
  ')"
  V_KIND="${GIT_VERDICT%%|*}"
  V_MSG="${GIT_VERDICT#*|}"
  if [ "$V_KIND" = "deny" ]; then
    DECISION="deny"
    REASON="$V_MSG"
  elif [ "$V_KIND" = "ask" ]; then
    DECISION="ask"
    REASON="$V_MSG"
  fi
fi

if [ "$DECISION" = "allow" ] && [ "$HARNESS" = "claude" ] && [ "${CLAUDECODE:-}" = "1" ] && [ -z "${CODEX_THREAD_ID:-}" ] && [ -z "${CODEX_CI:-}" ] && [ "${FLOW_MOD_LOADED:-}" != "1" ] && [ "$TOOL_NAME" = "Agent" ]; then
  if ! printf '%s' "$STDIN_PAYLOAD" | grep -q '"model"[[:space:]]*:[[:space:]]*"[^"]\+"'; then
    TIER="balanced"
    case "$AGENT_ID" in
      *plan-generator*|*prd-orchestrator*) TIER="frontier" ;;
      *researcher*) TIER="light" ;;
    esac
    TIER_FILE="$PROJECT_DIR/.claude/agents/flow-tier-${TIER}.md"
    if [ -f "$TIER_FILE" ]; then
      TIER_MODEL="$(awk '
        NR == 1 && /^---[[:space:]]*$/ { in_fm = 1; next }
        in_fm && /^---[[:space:]]*$/ { exit }
        in_fm && /^model:[[:space:]]*/ { v = $0; sub(/^model:[[:space:]]*/, "", v); gsub(/^["'\'']|["'\'']$/, "", v); gsub(/[[:space:]]+$/, "", v); print v; exit }
      ' "$TIER_FILE")"
      if [ -n "$TIER_MODEL" ] && [ "$TIER_MODEL" != "inherit" ]; then
        printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","updatedInput":{"model":"%s"}}}\n' "$(flow_json_escape "$TIER_MODEL")"
        exit 0
      fi
    fi
  fi
fi

CLEAN_REASON="$(flow_strip_xml_tags "$REASON")"
ESCAPED_REASON="$(flow_json_escape "$CLEAN_REASON")"

case "$HARNESS" in
  agy|antigravity)
    if [ "$DECISION" = "deny" ]; then
      printf '{"decision":"deny","reason":"%s"}\n' "$ESCAPED_REASON"
    elif [ "$DECISION" = "ask" ]; then
      printf '{"decision":"force_ask","reason":"%s"}\n' "$ESCAPED_REASON"
    else
      printf '{"decision":"allow"}\n'
    fi
    ;;
  cursor)
    if [ "$DECISION" = "deny" ]; then
      printf '{"permission":"deny","user_message":"%s"}\n' "$ESCAPED_REASON"
    elif [ "$DECISION" = "ask" ]; then
      printf '{"permission":"ask","user_message":"%s"}\n' "$ESCAPED_REASON"
    else
      printf '{"permission":"allow"}\n'
    fi
    ;;
  claude|vscode|*)
    if [ "$DECISION" = "deny" ]; then
      printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$ESCAPED_REASON"
    elif [ "$DECISION" = "ask" ]; then
      printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$ESCAPED_REASON"
    else
      printf '{}\n'
    fi
    ;;
esac
