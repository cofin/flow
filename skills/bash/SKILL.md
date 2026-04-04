---
name: bash
description: "Auto-activate for .sh files, #!/bin/bash, #!/usr/bin/env bash. Bash scripting expertise following Google Shell Style Guide. Produces shell scripts following Google Shell Style Guide with proper error handling, quoting, and safety patterns. Use when: writing shell scripts, automating tasks, processing text, or creating CLI tools. Covers error handling, variable quoting, function patterns, and portable scripting. Not for Python/Ruby scripts that happen to call shell commands."
---

# Bash Scripting

## Overview

Bash is the default shell on most Linux distributions. This skill covers idiomatic scripting patterns following the Google Shell Style Guide, with emphasis on safety, readability, and maintainability.

## Quick Reference

### Safety Header (always include)

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
```

| Flag | Effect |
|------|--------|
| `set -e` | Exit immediately on non-zero return |
| `set -u` | Error on unset variables |
| `set -o pipefail` | Pipe returns rightmost non-zero exit code |
| `IFS=$'\n\t'` | Safer word splitting (no space splitting) |

### Style Essentials

| Rule | Good | Bad |
|------|------|-----|
| Function declaration | `my_func() { ... }` | `function my_func { ... }` |
| Local variables | `local file_path="$1"` | `file_path=$1` |
| Constants | `readonly MAX_RETRIES=3` | `MAX_RETRIES=3` |
| Variable expansion | `"${var}"` | `$var` |
| Command substitution | `"$(command)"` | `` `command` `` |
| Declare + assign | `local out; out="$(cmd)"` | `local out="$(cmd)"` |
| File test | `[[ -f "${file}" ]]` | `[ -f $file ]` |

### Common ShellCheck Fixes

| Code | Issue | Fix |
|------|-------|-----|
| SC2086 | Unquoted variable | Double-quote: `"${var}"` |
| SC2046 | Unquoted command sub | Quote or use `mapfile` |
| SC2155 | Declare and assign together | Separate into two statements |
| SC2034 | Unused variable | Add `export` or `# shellcheck disable=SC2034` |

<workflow>

## Workflow

### Step 1: Start with the Safety Header

Every script begins with the shebang, strict mode, and a usage comment block describing purpose, usage, and examples.

### Step 2: Define Functions

Organize logic into functions. Use `local` for all function-scoped variables. Use `main()` as the entry point, called at the bottom with `main "$@"`.

### Step 3: Handle Arguments

Use `getopts` for simple flags, or manual `while [[ $# -gt 0 ]]` parsing for long options. Always validate required arguments and print usage on error.

### Step 4: Add Cleanup Traps

Use `trap cleanup EXIT` for any script that creates temporary files, acquires locks, or needs to restore state on failure.

### Step 5: Run ShellCheck

Validate the script with `shellcheck script.sh` before committing. Fix all warnings; disable specific rules only with a justifying comment.

</workflow>

<guardrails>

## Guardrails

- **Always quote variables** — unquoted variables cause word splitting and glob expansion bugs; use `"${var}"` everywhere
- **Always use ShellCheck** — run `shellcheck` on every script; it catches the majority of common bash pitfalls
- **Prefer functions over inline code** — functions with `local` variables prevent accidental global state leaks
- **Never use `eval`** unless absolutely necessary — it is the most common source of injection vulnerabilities in shell scripts
- **Use `[[ ]]` not `[ ]`** — double brackets prevent word splitting and support regex matching
- **Use `mktemp` for temporary files** — never hardcode `/tmp/myscript.tmp`; it creates race conditions
- **Avoid parsing `ls` output** — use globs (`*.txt`) or `find` with `-print0` and `read -d ''` for safe file iteration

</guardrails>

<validation>

### Validation Checkpoint

Before delivering a script, verify:

- [ ] Script starts with `#!/usr/bin/env bash` and `set -euo pipefail`
- [ ] All variables are quoted with `"${var}"`
- [ ] All function variables use `local`
- [ ] `trap cleanup EXIT` is set if the script creates temporary resources
- [ ] ShellCheck passes with no unacknowledged warnings
- [ ] Script has a usage/help function accessible via `-h` or `--help`

</validation>

<example>

## Example

A safe script template with error handling, argument parsing, and cleanup:

```bash
#!/usr/bin/env bash
#
# Deploy an application to the target environment.
#
# Usage:
#   deploy.sh [-v] [-e environment] <app_name>
#
set -euo pipefail
IFS=$'\n\t'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TMPDIR="$(mktemp -d)"

cleanup() {
    rm -rf "${TMPDIR}"
}
trap cleanup EXIT

usage() {
    cat <<EOF
Usage: $(basename "$0") [-v] [-e environment] <app_name>

Options:
  -v              Verbose output
  -e ENVIRONMENT  Target environment (default: staging)
  -h              Show this help
EOF
}

main() {
    local verbose=false
    local environment="staging"

    while getopts ":ve:h" opt; do
        case "${opt}" in
            v) verbose=true ;;
            e) environment="${OPTARG}" ;;
            h) usage; exit 0 ;;
            :) echo "Error: -${OPTARG} requires an argument" >&2; exit 1 ;;
            ?) echo "Error: Unknown option -${OPTARG}" >&2; exit 1 ;;
        esac
    done
    shift $((OPTIND - 1))

    if [[ $# -eq 0 ]]; then
        echo "Error: app_name is required" >&2
        usage >&2
        exit 1
    fi

    local app_name="$1"

    if [[ "${verbose}" == true ]]; then
        echo "Deploying ${app_name} to ${environment}..."
    fi

    # Build and deploy logic here
    echo "Deployed ${app_name} to ${environment} successfully."
}

main "$@"
```

</example>

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Style Guide](references/style.md)**
  - Google Shell Style Guide patterns: file headers, function naming, variable naming, quoting rules, error handling.
- **[Common Patterns](references/patterns.md)**
  - Argument parsing (getopts), trap for cleanup, here-docs, process substitution, array manipulation, associative arrays.
- **[Safety & Defensive Scripting](references/safety.md)**
  - Shellcheck compliance, avoiding common pitfalls, handling spaces in filenames, proper exit codes, signal handling.

---

## Official References

- <https://google.github.io/styleguide/shellguide.html>
- <https://www.gnu.org/software/bash/manual/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Bash](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/bash.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
