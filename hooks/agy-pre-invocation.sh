#!/usr/bin/env bash
#
# agy-pre-invocation.sh - Antigravity PreInvocation hook for Flow priming.
#
# Antigravity has no SessionStart event, so priming context is injected on the
# first model invocation of a conversation via injectSteps. A marker file keyed
# by conversationId (plus the invocationNum field) keeps the injection
# once-per-conversation. Always exits 0; runtime dependency policy: shell only.
#
set -u

get_script_dir() {
    local source="${BASH_SOURCE[0]:-$0}"
    local dir
    while [[ -h "${source}" ]]; do
        dir="$(cd -P "$(dirname "${source}")" && pwd)"
        source="$(readlink "${source}")"
        [[ "${source}" != /* ]] && source="${dir}/${source}"
    done
    cd -P "$(dirname "${source}")" && pwd
}

json_string_field() {
    # $1: json text, $2: field name
    printf '%s' "$1" | sed -n 's/.*"'"$2"'"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1
}

json_number_field() {
    printf '%s' "$1" | sed -n 's/.*"'"$2"'"[[:space:]]*:[[:space:]]*\(-\{0,1\}[0-9][0-9]*\).*/\1/p' | head -n1
}

escape_json() {
    awk '
        {
            line = $0
            gsub(/\\/, "\\\\", line)
            gsub(/"/, "\\\"", line)
            gsub(/\t/, "\\t", line)
            gsub(/\r/, "\\r", line)
            out = out line "\\n"
        }
        END { printf "\"%s\"", out }
    '
}

main() {
    local input=""
    if [[ ! -t 0 ]]; then
        input="$(cat || true)"
    fi

    local conversation_id invocation_num artifact_dir
    conversation_id="$(json_string_field "${input}" "conversationId")"
    invocation_num="$(json_number_field "${input}" "invocationNum")"
    artifact_dir="$(json_string_field "${input}" "artifactDirectoryPath")"

    # Inject only on the conversation's first invocation when the field is present.
    if [[ -n "${invocation_num}" && "${invocation_num}" != "0" ]]; then
        printf '{"injectSteps": []}\n'
        return 0
    fi

    local marker_dir="${artifact_dir:-${TMPDIR:-/tmp}}"
    [[ -d "${marker_dir}" ]] || marker_dir="${TMPDIR:-/tmp}"
    local marker="${marker_dir}/.flow-primed-${conversation_id:-unknown}"
    if [[ -f "${marker}" ]]; then
        printf '{"injectSteps": []}\n'
        return 0
    fi

    local script_dir context
    script_dir="$(get_script_dir || pwd)"
    if ! context="$("${script_dir}/detect-env.sh" 2>/dev/null)"; then
        context="No project context resolved."
    fi

    local escaped
    escaped="$(printf '%s\n' "${context}" | escape_json)"
    printf '{"injectSteps": [{"ephemeralMessage": %s}]}\n' "${escaped}"

    touch "${marker}" 2>/dev/null || true
    return 0
}

main "$@"
exit 0
