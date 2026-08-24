#!/usr/bin/env bash
# Claude PreToolUse Git guardrail. Requires Bash and jq.
set -euo pipefail
shopt -s extglob

deny() {
  printf 'Blocked by Flow Git guardrail: %s\n' "$1" >&2
  exit 2
}

if ! command -v jq >/dev/null 2>&1; then
  deny "jq is required to parse the hook payload"
fi

INPUT=$(cat)
if ! COMMAND=$(printf '%s' "$INPUT" | jq -er '
  .tool_input.command
  | select(type == "string" and test("\\S"))
' 2>/dev/null); then
  deny "expected a non-empty string at .tool_input.command"
fi

# Fail closed rather than trying to partially parse shell syntax or expansion.
case "$COMMAND" in
  *'$'*|*'`'*|*';'*|*'&'*|*'|'*|*'<'*|*'>'*|*'('*|*')'*|*'{'*|*'}'*|*'\'*|*$'\n'*|*$'\r'*)
    deny "shell expansion or metacharacters cannot be classified safely"
    ;;
esac

# Lex for classification only. This recognizes plain tokens and whole-token single or
# double quotes without evaluating escapes, expansions, substitutions, or shell syntax.
TOKENS=()
TOKEN_QUOTED=()
current=''
quote=''
quoted=0
command_length=${#COMMAND}

for ((position = 0; position < command_length; position++)); do
  character=${COMMAND:position:1}
  if [[ -n "$quote" ]]; then
    if [[ "$character" == "$quote" ]]; then
      quote=''
      if ((position + 1 < command_length)); then
        next_character=${COMMAND:position+1:1}
        [[ "$next_character" == ' ' || "$next_character" == $'\t' ]] ||
          deny "shell quote concatenation cannot be classified safely"
      fi
    else
      current+=$character
    fi
  elif [[ "$character" == ' ' || "$character" == $'\t' ]]; then
    if [[ -n "$current" || "$quoted" == 1 ]]; then
      TOKENS+=("$current")
      TOKEN_QUOTED+=("$quoted")
      current=''
      quoted=0
    fi
  elif [[ "$character" == "'" || "$character" == '"' ]]; then
    [[ -z "$current" ]] || deny "shell quote concatenation cannot be classified safely"
    quote=$character
    quoted=1
  else
    current+=$character
  fi
done

[[ -z "$quote" ]] || deny "shell quote concatenation cannot be classified safely"
if [[ -n "$current" || "$quoted" == 1 ]]; then
  TOKENS+=("$current")
  TOKEN_QUOTED+=("$quoted")
fi

for ((token_index = 0; token_index < ${#TOKENS[@]}; token_index++)); do
  if [[ "${TOKEN_QUOTED[token_index]}" == 0 ]]; then
    case "${TOKENS[token_index]}" in
      *'*'*|*'?'*|*'['*|*']'*)
        deny "unquoted pathname expansion cannot be classified safely"
        ;;
    esac
  fi
done

normalize_token() {
  local token=$1
  token=${token##+([\;&\|\(])}
  token=${token%%+([\;&\|\)])}
  printf '%s' "$token"
}

is_separator() {
  case "$1" in
    \&\&|\|\||\||\;|\&|\(|\)) return 0 ;;
    *) return 1 ;;
  esac
}

scan_arguments_for() {
  local command_name=$1
  local start=$2
  local index token
  local delete_seen=0
  local force_seen=0
  local tag_list_mode=0
  local clean_dry_run=0
  local clean_interactive=0

  for ((index = start; index < ${#TOKENS[@]}; index++)); do
    token=$(normalize_token "${TOKENS[index]}")
    is_separator "$token" && break

    case "$command_name" in
      reset)
        if [[ "$token" == "--hard" || "$token" == --hard=* ]]; then
          deny "git reset --hard is prohibited"
        fi
        ;;
      clean)
        if [[ "$token" == "--dry-run" || "$token" =~ ^-[^-]*n ]]; then
          clean_dry_run=1
        fi
        if [[ "$token" == "--interactive" || "$token" =~ ^-[^-]*i ]]; then
          clean_interactive=1
        fi
        ;;
      branch)
        if [[ "$token" == "-D" ]]; then
          deny "forced branch deletion is prohibited"
        fi
        if [[ "$token" == "--delete" || "$token" =~ ^-[^-]*d ]]; then
          delete_seen=1
        fi
        if [[ "$token" == "--force" || "$token" =~ ^-[^-]*f ]]; then
          force_seen=1
        fi
        if ((delete_seen && force_seen)); then
          deny "forced branch deletion is prohibited"
        fi
        ;;
      tag)
        case "$token" in
          -l|--list|-n|-n[0-9]*|--contains|--no-contains|--points-at|--merged|--no-merged|--ignore-case)
            tag_list_mode=1
            ;;
          --list=*|--contains=*|--no-contains=*|--points-at=*|--merged=*|--no-merged=*|--sort=*|--format=*|--column|--column=*)
            tag_list_mode=1
            ;;
          -d|--delete|-f|--force|-a|--annotate|-s|--sign|-u|--local-user|--local-user=*)
            deny "Git tag mutation is prohibited"
            ;;
          --)
            ;;
          -*)
            deny "unclassifiable git tag option"
            ;;
          *)
            ((tag_list_mode)) || deny "Git tag creation or update is prohibited"
            ;;
        esac
        ;;
    esac
  done

  if [[ "$command_name" == "clean" ]]; then
    if ((clean_interactive || !clean_dry_run)); then
      deny "git clean requires an explicit non-interactive dry-run option"
    fi
  fi
}

for ((i = 0; i < ${#TOKENS[@]}; i++)); do
  token=$(normalize_token "${TOKENS[i]}")
  [[ "$token" == "git" || "$token" == */git ]] || continue

  j=$((i + 1))
  while ((j < ${#TOKENS[@]})); do
    candidate=$(normalize_token "${TOKENS[j]}")
    case "$candidate" in
      --no-pager|--paginate|--no-replace-objects|--bare|--literal-pathspecs|--glob-pathspecs|--noglob-pathspecs|--icase-pathspecs|-p|-P)
        ((j += 1))
        ;;
      -C|-c|--git-dir|--work-tree|--namespace|--super-prefix|--config-env)
        ((j + 1 < ${#TOKENS[@]})) || deny "incomplete Git global option"
        if [[ "$candidate" == "-c" ]]; then
          config=${TOKENS[j + 1],,}
          if [[ "$config" == alias.* ]]; then
            deny "Git alias configuration cannot be classified safely"
          fi
        fi
        ((j += 2))
        ;;
      -c?*)
        config=${candidate:2}
        config=${config,,}
        if [[ "$config" == alias.* ]]; then
          deny "Git alias configuration cannot be classified safely"
        fi
        ((j += 1))
        ;;
      --git-dir=*|--work-tree=*|--namespace=*|--super-prefix=*|--config-env=*)
        ((j += 1))
        ;;
      -*)
        deny "unclassifiable Git global option"
        ;;
      *)
        break
        ;;
    esac
  done

  ((j < ${#TOKENS[@]})) || continue
  subcommand=$(normalize_token "${TOKENS[j]}")
  case "$subcommand" in
    push)
      deny "git push requires an explicit user action"
      ;;
    reset|clean|tag|branch)
      scan_arguments_for "$subcommand" "$((j + 1))"
      ;;
    add|am|apply|archive|bisect|blame|bundle|cat-file|checkout|cherry|cherry-pick|clone|commit|config|describe|diff|difftool|fetch|for-each-ref|format-patch|fsck|gc|grep|help|init|log|ls-files|ls-tree|maintenance|merge|merge-base|mergetool|mv|notes|pull|range-diff|rebase|reflog|remote|repack|replace|request-pull|restore|rev-list|rev-parse|revert|rm|shortlog|show|show-branch|sparse-checkout|stage|stash|status|submodule|switch|symbolic-ref|update-index|version|whatchanged|worktree)
      ;;
    *)
      deny "unknown Git subcommand cannot be classified safely"
      ;;
  esac
done

exit 0
