#!/usr/bin/env bash
#
# detect-env.sh - Emit Flow priming context from the OKF bundles as markdown.
#
# Output mirrors `tools/priming.py --markdown` (the dev/CI oracle). The
# session-start dispatchers wrap this output in harness-appropriate JSON.
# Runtime dependency policy: shell + awk only — no Python at runtime.
#
set -euo pipefail

find_project_root() {
    local dir
    dir="$(pwd)"
    while [[ -n "${dir}" && "${dir}" != "/" ]]; do
        if [[ -d "${dir}/.agents" ]]; then
            printf '%s\n' "${dir}"
            return 0
        fi
        dir="$(dirname "${dir}")"
    done
    pwd
}

# Read a top-level string value from .agents/config.json without a JSON parser.
config_value() {
    local file="$1" key="$2"
    [[ -f "${file}" ]] || return 0
    sed -n 's/.*"'"${key}"'"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "${file}" | head -n1
}

# Print frontmatter value for a key (first match), stripped of quotes.
fm_get() {
    local file="$1" key="$2"
    awk -v key="${key}" '
        NR == 1 && $0 != "---" { exit }
        NR > 1 && $0 == "---" { exit }
        NR > 1 {
            prefix = key ":"
            if (index($0, prefix) == 1) {
                value = substr($0, length(prefix) + 1)
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
                gsub(/^["'\'']|["'\'']$/, "", value)
                print value
                exit
            }
        }
    ' "${file}"
}

# Print file body with the leading frontmatter block removed.
strip_frontmatter() {
    awk '
        NR == 1 && $0 == "---" { in_fm = 1; next }
        in_fm && $0 == "---" { in_fm = 0; body = 1; next }
        in_fm { next }
        { print }
    ' "$1"
}

# First 5 non-empty, non-heading body lines.
extract_identity() {
    local file="$1"
    [[ -f "${file}" ]] || return 0
    strip_frontmatter "${file}" | awk '
        {
            line = $0
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
            if (line == "" || line ~ /^#/) next
            print line
            if (++count == 5) exit
        }
    '
}

# Truth markers block, else first 10 list items, else first 200 chars of prose.
extract_truths() {
    local file="$1"
    [[ -f "${file}" ]] || return 0
    strip_frontmatter "${file}" | awk '
        /<!-- truth: start -->/ { in_truth = 1; has_truth = 1; next }
        /<!-- truth: end -->/ { in_truth = 0; next }
        in_truth { truth = truth $0 "\n" }
        {
            line = $0
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
            if (line ~ /^(- |\* |1\. )/ && list_count < 10) {
                list[list_count++] = line
            }
            if (line !~ /^#/) plain = plain $0 "\n"
        }
        END {
            if (has_truth) {
                gsub(/^[\n[:space:]]+|[\n[:space:]]+$/, "", truth)
                print truth
            } else if (list_count > 0) {
                for (i = 0; i < list_count; i++) print list[i]
            } else {
                gsub(/^[\n[:space:]]+|[\n[:space:]]+$/, "", plain)
                print substr(plain, 1, 200)
            }
        }
    '
}

state_of() {
    local file="$1" fallback="$2" value
    value="$(fm_get "${file}" "state")"
    if [[ -z "${value}" ]]; then
        value="$(fm_get "${file}" "status")"
    fi
    printf '%s\n' "${value:-${fallback}}"
}

main() {
    local project_root bundles_dir knowledge_dir config_file
    project_root="$(find_project_root)"
    config_file="${project_root}/.agents/config.json"

    bundles_dir="${project_root}/.agents/bundles"
    knowledge_dir="${bundles_dir}/knowledge"
    local cfg_bundles cfg_knowledge
    cfg_bundles="$(config_value "${config_file}" "bundles_dir")"
    cfg_knowledge="$(config_value "${config_file}" "knowledge_dir")"
    if [[ -n "${cfg_bundles}" ]]; then
        bundles_dir="${project_root}/${cfg_bundles}"
        knowledge_dir="${bundles_dir}/knowledge"
    fi
    if [[ -n "${cfg_knowledge}" ]]; then
        knowledge_dir="${project_root}/${cfg_knowledge}"
    fi

    local blocks=()

    # --- Project Purpose ---
    local identity
    identity="$(extract_identity "${bundles_dir}/product/product.md")"
    if [[ -n "${identity}" ]]; then
        blocks+=("## Project Purpose
${identity}")
    fi

    # --- Core Project Invariants ---
    local truths="" filename source_path heading file_truths
    for filename in tech-stack.md workflow.md patterns.md; do
        if [[ "${filename}" == "tech-stack.md" ]]; then
            source_path="${bundles_dir}/product/${filename}"
        else
            source_path="${knowledge_dir}/${filename}"
        fi
        file_truths="$(extract_truths "${source_path}")"
        if [[ -n "${file_truths}" ]]; then
            # Mirror Python str.capitalize(): first char upper, rest unchanged-lower
            heading="$(printf '%s' "${filename:0:1}" | tr '[:lower:]' '[:upper:]')${filename:1}"
            if [[ -n "${truths}" ]]; then
                truths="${truths}

"
            fi
            truths="${truths}### ${heading} Invariants
${file_truths}"
        fi
    done
    if [[ -n "${truths}" ]]; then
        blocks+=("## Core Project Invariants
${truths}")
    fi

    # --- Active Flows & Tasks ---
    local flow_lines="" spec_dir spec_file flow_state flow_id flow_title flow_desc rel_spec
    if [[ -d "${bundles_dir}/specs" ]]; then
        for spec_dir in $(find "${bundles_dir}/specs" -mindepth 1 -maxdepth 1 -type d | sort); do
            spec_file="${spec_dir}/spec.md"
            [[ -f "${spec_file}" ]] || continue
            flow_state="$(state_of "${spec_file}" "planned")"
            case "${flow_state}" in
                planned|active) ;;
                *) continue ;;
            esac
            flow_id="$(fm_get "${spec_file}" "flow_id")"
            [[ -z "${flow_id}" ]] && flow_id="$(fm_get "${spec_file}" "id")"
            [[ -z "${flow_id}" ]] && flow_id="$(basename "${spec_dir}")"
            flow_title="$(fm_get "${spec_file}" "title")"
            [[ -z "${flow_title}" ]] && flow_title="${flow_id}"
            flow_desc="$(fm_get "${spec_file}" "description")"
            rel_spec="${spec_file#"${project_root}"/}"

            flow_lines="${flow_lines}
### Flow: [${flow_title}](${rel_spec}) (${flow_state})"
            if [[ -n "${flow_desc}" ]]; then
                flow_lines="${flow_lines}
*${flow_desc}*"
            fi

            local task_lines="" task_file task_state task_title task_priority rel_task
            if [[ -d "${spec_dir}/tasks" ]]; then
                for task_file in $(find "${spec_dir}/tasks" -mindepth 1 -maxdepth 1 -name '*.md' -type f | sort); do
                    task_state="$(state_of "${task_file}" "open")"
                    case "${task_state}" in
                        open|in_progress|blocked) ;;
                        *) continue ;;
                    esac
                    task_title="$(fm_get "${task_file}" "title")"
                    [[ -z "${task_title}" ]] && task_title="$(basename "${task_file}" .md)"
                    task_priority="$(fm_get "${task_file}" "priority")"
                    [[ -z "${task_priority}" ]] && task_priority="P2"
                    rel_task="${task_file#"${project_root}"/}"
                    task_lines="${task_lines}
- [${task_priority}] [${task_title}](${rel_task}) (${task_state})"
                done
            fi
            if [[ -n "${task_lines}" ]]; then
                flow_lines="${flow_lines}
Pending Tasks:${task_lines}"
            else
                flow_lines="${flow_lines}
No active tasks."
            fi
        done
    fi
    if [[ -n "${flow_lines}" ]]; then
        blocks+=("## Active Flows & Tasks${flow_lines}")
    fi

    # --- Custom Project Skills ---
    local skill_lines="" skill_root skill_dir skill_file skill_name skill_desc rel_skill seen=""
    for skill_root in "${project_root}/.agents/skills" "${bundles_dir}/skills"; do
        [[ -d "${skill_root}" ]] || continue
        for skill_dir in $(find "${skill_root}" -mindepth 1 -maxdepth 1 -type d | sort); do
            local dir_name
            dir_name="$(basename "${skill_dir}")"
            case " ${seen} " in
                *" ${dir_name} "*) continue ;;
            esac
            skill_file="${skill_dir}/SKILL.md"
            [[ -f "${skill_file}" ]] || continue
            skill_name="$(fm_get "${skill_file}" "name")"
            [[ -z "${skill_name}" ]] && skill_name="${dir_name}"
            skill_desc="$(fm_get "${skill_file}" "description")"
            rel_skill="${skill_file#"${project_root}"/}"
            skill_lines="${skill_lines}
- **[${skill_name}](${rel_skill})**: ${skill_desc}"
            seen="${seen} ${dir_name}"
        done
    done
    if [[ -n "${skill_lines}" ]]; then
        blocks+=("## Custom Project Skills${skill_lines}")
    fi

    # --- Emit ---
    if [[ ${#blocks[@]} -eq 0 ]]; then
        printf 'No project context resolved.\n'
        return 0
    fi
    local i
    for i in "${!blocks[@]}"; do
        if [[ "${i}" -gt 0 ]]; then
            printf '\n\n'
        fi
        printf '%s' "${blocks[${i}]}"
    done
    printf '\n'
}

main "$@"
