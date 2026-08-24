#!/usr/bin/env bash
# Claude PreToolUse Git guardrail: deny recognizable destructive Git operations.
# Anything the lexer cannot classify is allowed; this catches honest mistakes,
# not deliberate obfuscation.
set -euo pipefail
shopt -s extglob

deny() {
  printf 'Blocked by Flow Git guardrail: %s\n' "$1" >&2
  exit 2
}

if ! command -v jq >/dev/null 2>&1; then
  printf 'Flow Git guardrail: jq is unavailable; skipping Git classification\n' >&2
  exit 0
fi

INPUT=$(cat)
if ! COMMAND=$(printf '%s' "$INPUT" | jq -er '
  .tool_input.command
  | select(type == "string" and test("\\S"))
' 2>/dev/null); then
  deny "expected a non-empty string at .tool_input.command"
fi

# Byte-indexed scanning keeps the lexers linear for large commands.
export LC_ALL=C

# Fast path: without a literal Git lexeme (quotes removed) there is nothing to classify.
UNQUOTED_COMMAND=${COMMAND//[\'\"]/}
[[ "$UNQUOTED_COMMAND" == *[gG][iI][tT]* ]] || exit 0

# The Bash hook matcher sees every shell command. Normalize raw word structure
# without evaluation and route literal Git lexemes to classification.
possible_git=0
relevance_token=''
expect_executable=1
skip_redirection_target=0
executable=''
evaluator_mode=''
evaluator_nested_git=0
git_boundary_pattern='(^|[=/[:space:]`(])[gG][iI][tT](\.[eE][xX][eE])?($|[/:[:space:]`)])'

classify_relevance_token() {
  local token=$relevance_token
  local basename=$token
  local contains_git=0

  [[ -n "$token" ]] || return 0
  if [[ "$token" =~ $git_boundary_pattern ]]; then
    contains_git=1
  fi
  [[ "$token" =~ ([^/]*)$ ]] && basename=${BASH_REMATCH[1]}
  case "${basename,,}" in
    git-*) contains_git=1 ;;
  esac
  if [[ -n "$evaluator_mode" ]]; then
    if ((contains_git)); then
      evaluator_nested_git=1
      possible_git=1
    fi
    [[ "$evaluator_mode" == command_string ]] && evaluator_mode=''
    return 0
  fi
  if ((contains_git)); then
    possible_git=1
    return 0
  fi
  if ((skip_redirection_target)); then
    skip_redirection_target=0
    return 0
  fi
  if ((expect_executable)); then
    [[ "$token" =~ ^[a-zA-Z_][a-zA-Z0-9_]*= ]] && return 0
    case "$token" in
      '!'|time|exec|nice|sudo|env|command|if|then|elif|else|while|until|do)
        return 0
        ;;
      eval)
        executable=$token
        evaluator_mode=eval_arguments
        expect_executable=0
        return 0
        ;;
    esac
    executable=$token
    expect_executable=0
  elif [[ ${executable##*/} =~ ^(bash|sh|dash|ksh|zsh)$ && "$token" =~ ^-[a-zA-Z]*c[a-zA-Z]*$ ]]; then
    evaluator_mode=command_string
  fi
  return 0
}

relevance_quote=''
command_length=${#COMMAND}
# Runs of ordinary characters are consumed in one step so scanning stays linear.
special_pattern=$'[[:space:]$`\'"\\\\\\*\\?\\[<>;&|(){}]'
position=0
while ((position < command_length)); do
  rest=${COMMAND:position}
  if [[ -n "$relevance_quote" ]]; then
    if [[ "$relevance_quote" == "'" ]]; then
      segment=${rest%%\'*}
    else
      segment=${rest%%[\"\$\`\\]*}
    fi
    relevance_token+=$segment
    position=$((position + ${#segment}))
    ((position < command_length)) || break
    character=${COMMAND:position:1}
    if [[ "$character" == "$relevance_quote" ]]; then
      relevance_quote=''
    elif [[ "$character" == '$' || "$character" == '`' ]]; then
      relevance_token+=$character
    elif ((position + 1 < command_length)); then
      position=$((position + 1))
      relevance_token+=${COMMAND:position:1}
    fi
    position=$((position + 1))
    continue
  fi
  segment=${rest%%$special_pattern*}
  if [[ -n "$segment" ]]; then
    relevance_token+=$segment
    position=$((position + ${#segment}))
    ((position < command_length)) || break
  fi
  character=${COMMAND:position:1}
  case "$character" in
    "'"|'"')
      relevance_quote=$character
      ;;
    '\')
      ((position + 1 < command_length)) || break
      position=$((position + 1))
      relevance_token+=${COMMAND:position:1}
      ;;
    ' '|$'\t')
      classify_relevance_token
      relevance_token=''
      ;;
    '<'|'>')
      if [[ "$relevance_token" =~ ^[0-9]+$ && "$expect_executable" == 1 ]]; then
        relevance_token=''
      else
        classify_relevance_token
        relevance_token=''
      fi
      skip_redirection_target=1
      ;;
    ';'|'&'|'|'|'('|')'|'{'|'}'|$'\n'|$'\r')
      classify_relevance_token
      relevance_token=''
      expect_executable=1
      skip_redirection_target=0
      executable=''
      evaluator_mode=''
      ;;
    *)
      relevance_token+=$character
      ;;
  esac
  position=$((position + 1))
done
classify_relevance_token
((possible_git)) || exit 0
((evaluator_nested_git)) && deny "run Git directly rather than through eval or a shell -c string"

# Lex for classification only: words split on whitespace, command separators,
# and substitution delimiters, with quotes removed. Escapes and expansions are
# not evaluated; a separator token marks each command boundary.
TOKENS=()
current=''
quote=''
quoted=0
command_length=${#COMMAND}
position=0

flush_token() {
  if [[ -n "$current" || "$quoted" == 1 ]]; then
    TOKENS+=("$current")
    current=''
    quoted=0
  fi
}

while ((position < command_length)); do
  rest=${COMMAND:position}
  if [[ -n "$quote" ]]; then
    segment=${rest%%"$quote"*}
    current+=$segment
    position=$((position + ${#segment}))
    ((position < command_length)) || break
    quote=''
    position=$((position + 1))
    continue
  fi
  segment=${rest%%[[:space:]\'\"\;\&\|\(\)\`]*}
  current+=$segment
  position=$((position + ${#segment}))
  ((position < command_length)) || break
  character=${COMMAND:position:1}
  case "$character" in
    "'"|'"')
      quote=$character
      quoted=1
      ;;
    [[:space:]])
      flush_token
      ;;
    *)
      flush_token
      TOKENS+=(";")
      ;;
  esac
  position=$((position + 1))
done
flush_token

normalize_token() {
  local token=$1
  while [[ -n "$token" && "${token:0:1}" == [\;\&\|\(\{\$\`] ]]; do
    token=${token:1}
  done
  while [[ -n "$token" && "${token: -1}" == [\;\&\|\)\}] ]]; do
    token=${token::-1}
  done
  NORMALIZED=$token
}

ends_command() {
  [[ -n "$1" && "${1: -1}" == [\;\&\|\)\}] ]]
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
    raw=${TOKENS[index]}
    normalize_token "$raw"
    token=$NORMALIZED
    if [[ -z "$token" ]] || is_separator "$raw"; then
      break
    fi

    case "$command_name" in
      reset)
        if [[ "$token" == "--hard" || "$token" == --hard=* ]]; then
          deny "git reset --hard is prohibited"
        fi
        ;;
      clean)
        if [[ "$token" == "--dry-run" || "$token" =~ ^-[^-]*n ]]; then
          clean_dry_run=1
        elif [[ "$token" == "--no-dry-run" ]]; then
          clean_dry_run=0
        fi
        if [[ "$token" == "--interactive" || "$token" =~ ^-[^-]*i ]]; then
          clean_interactive=1
        fi
        ;;
      branch)
        if [[ "$token" =~ ^-[^-]*D ]]; then
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
          -l|--list|-n|-n[0-9]*|--contains|--no-contains|--points-at|--merged|--no-merged)
            tag_list_mode=1
            ;;
          --contains=*|--no-contains=*|--points-at=*|--merged=*|--no-merged=*)
            tag_list_mode=1
            ;;
          -i|--ignore-case|--sort=*|--format=*|--column|--column=*|--no-column|--color|--color=*|--no-color|--omit-empty)
            ;;
          -d|--delete|-f|--force|-a|--annotate|-s|--sign|-u|--local-user|--local-user=*)
            deny "Git tag mutation is prohibited"
            ;;
          --|-*)
            ;;
          *)
            ((tag_list_mode)) || deny "Git tag creation or update is prohibited"
            ;;
        esac
        ;;
      fetch|pull)
        case "$token" in
          --t*|--prune-*|-t|-P|tag|*tags/*)
            deny "explicit tag fetching or pruning is prohibited"
            ;;
        esac
        if [[ "$token" =~ ^-[^-]*[tP] ]]; then
          deny "explicit tag fetching or pruning is prohibited"
        fi
        ;;
      remote)
        case "$token" in
          --t*|--mirror*)
            deny "remote tag import configuration is prohibited"
            ;;
        esac
        ;;
      config)
        case "${token,,}" in
          *tagopt*|*prunetags*|remote.*.fetch|*tags/*)
            deny "Git tag fetching configuration is prohibited"
            ;;
        esac
        ;;
      symbolic-ref)
        if [[ "$token" == *tags/* ]]; then
          deny "Git tag mutation is prohibited"
        fi
        ;;
    esac
    ends_command "$raw" && break
  done

  if [[ "$command_name" == "clean" ]]; then
    if ((clean_interactive || !clean_dry_run)); then
      deny "git clean requires an explicit non-interactive dry-run option"
    fi
  fi
}

is_tag_fetch_config() {
  local config=${1,,}
  case "$config" in
    remote.*.tagopt=--no-tags)
      return 1
      ;;
    remote.*.tagopt*|*prunetags*|remote.*.fetch=*tags/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_tag_fetch_config_env() {
  local config=${1,,}
  case "$config" in
    remote.*.tagopt=*|remote.*.prunetags=*|fetch.prunetags=*|remote.*.fetch=*) return 0 ;;
    *) return 1 ;;
  esac
}

classify_git_subcommand() {
  local subcommand=$1
  local argument_start=$2

  case "$subcommand" in
    push)
      deny "git push requires an explicit user action"
      ;;
    reset|clean|tag|branch|fetch|pull|remote|config|symbolic-ref)
      scan_arguments_for "$subcommand" "$argument_start"
      ;;
  esac
}

for ((i = 0; i < ${#TOKENS[@]}; i++)); do
  normalize_token "${TOKENS[i]}"
  token=$NORMALIZED
  case "$token" in
    GIT_CONFIG_PARAMETERS=*|GIT_CONFIG_COUNT=*|GIT_CONFIG_KEY_*=*|GIT_CONFIG_VALUE_*=*)
      deny "Git configuration environment cannot be classified safely"
      ;;
  esac
  executable_basename=$token
  [[ "$token" =~ ([^/]*)$ ]] && executable_basename=${BASH_REMATCH[1]}
  executable_basename=${executable_basename,,}
  executable_basename=${executable_basename%.exe}
  if [[ "$executable_basename" == git-* ]]; then
    classify_git_subcommand "${executable_basename#git-}" "$((i + 1))"
    continue
  fi
  [[ "$executable_basename" == "git" ]] || continue

  j=$((i + 1))
  tag_fetch_config_seen=0
  while ((j < ${#TOKENS[@]})); do
    normalize_token "${TOKENS[j]}"
    candidate=$NORMALIZED
    case "$candidate" in
      --no-pager|--paginate|--no-replace-objects|--bare|--literal-pathspecs|--glob-pathspecs|--noglob-pathspecs|--icase-pathspecs|-p|-P)
        ((j += 1))
        ;;
      -C|-c|--git-dir|--work-tree|--namespace|--super-prefix|--config-env)
        ((j + 1 < ${#TOKENS[@]})) || break
        if [[ "$candidate" == "-c" ]]; then
          config=${TOKENS[j + 1],,}
          if [[ "$config" == alias.* ]]; then
            deny "Git alias configuration cannot be classified safely"
          fi
          is_tag_fetch_config "$config" && tag_fetch_config_seen=1
        elif [[ "$candidate" == "--config-env" ]]; then
          config=${TOKENS[j + 1],,}
          is_tag_fetch_config_env "$config" && tag_fetch_config_seen=1
        fi
        ((j += 2))
        ;;
      -c?*)
        config=${candidate:2}
        config=${config,,}
        if [[ "$config" == alias.* ]]; then
          deny "Git alias configuration cannot be classified safely"
        fi
        is_tag_fetch_config "$config" && tag_fetch_config_seen=1
        ((j += 1))
        ;;
      --config-env=*)
        config=${candidate#--config-env=}
        is_tag_fetch_config_env "$config" && tag_fetch_config_seen=1
        ((j += 1))
        ;;
      -*)
        ((j += 1))
        ;;
      *)
        break
        ;;
    esac
  done

  ((j < ${#TOKENS[@]})) || continue
  normalize_token "${TOKENS[j]}"
  subcommand=${NORMALIZED,,}
  if ((tag_fetch_config_seen)) && [[ "$subcommand" == fetch || "$subcommand" == pull ]]; then
    deny "Git configuration enabling tag fetching or pruning is prohibited"
  fi
  classify_git_subcommand "$subcommand" "$((j + 1))"
done

exit 0
