# Bash Style Guide

Based on the [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html).

## File Header

```bash
#!/usr/bin/env bash
#
# Brief description of the script's purpose.
#
# Usage:
#   script_name.sh [options] <arguments>
#
# Examples:
#   script_name.sh --verbose /path/to/input
```

## Strict Mode

Always start scripts with:

```bash
set -euo pipefail
```

| Flag | Meaning |
|------|---------|
| `-e` | Exit on error |
| `-u` | Error on undefined variables |
| `-o pipefail` | Pipe fails if any command fails |

## Function Naming

Use lowercase with underscores. Use `::` for namespacing in libraries.

```bash
# Simple function
process_file() {
    local file="$1"
    # ...
}

# Namespaced (for libraries)
mylib::validate_input() {
    local input="$1"
    # ...
}
```

## Function Declarations

Use the `name()` form, not `function name`.

```bash
# Good
my_function() {
    local arg1="$1"
    local arg2="$2"
    # ...
}

# Bad
function my_function {
    # ...
}
```

## Variable Naming

```bash
# Local variables: lowercase with underscores
local file_path="/tmp/data.txt"
local line_count=0

# Global/environment variables: uppercase with underscores
readonly MAX_RETRIES=3
export DATABASE_URL="postgresql://localhost/mydb"

# Constants: uppercase, declared readonly
readonly CONFIG_DIR="/etc/myapp"
readonly VERSION="1.0.0"
```

## Quoting Rules

**Always quote variables unless you specifically need word splitting or glob expansion.**

```bash
# Always quote
echo "${name}"
cp "${source_file}" "${dest_dir}/"
if [[ "${status}" == "active" ]]; then

# Quote command substitutions
local output
output="$(some_command)"

# Arrays: quote expansions
local -a files=("file one.txt" "file two.txt")
for f in "${files[@]}"; do
    process_file "${f}"
done

# No quotes needed for:
# - Arithmetic: (( count++ ))
# - [[ ]] pattern matching right side: [[ "${str}" == *.txt ]]
```

## Brace Expansion for Variables

```bash
# Use ${var} when:
# - Adjacent to other characters
echo "${prefix}_suffix"
echo "path/${dir}/file"

# Plain $var is acceptable when unambiguous
echo "$HOME"
```

## Conditionals

Use `[[ ]]` instead of `[ ]`:

```bash
# String comparison
if [[ "${answer}" == "yes" ]]; then
    echo "Confirmed"
fi

# Pattern matching
if [[ "${filename}" == *.tar.gz ]]; then
    tar xzf "${filename}"
fi

# Regex matching
if [[ "${email}" =~ ^[a-zA-Z0-9.]+@[a-zA-Z0-9.]+$ ]]; then
    echo "Valid email"
fi

# Numeric comparison (use (( )))
if (( count > 10 )); then
    echo "Too many"
fi
```

## Error Handling

```bash
# Print errors to stderr
err() {
    echo "[ERROR] $(date +'%Y-%m-%d %H:%M:%S') $*" >&2
}

# Usage
if ! do_something; then
    err "Failed to do something"
    exit 1
fi
```

## Return Values

Use `return` for functions, `exit` for scripts. Prefer returning status codes over echoing "true"/"false".

```bash
is_valid_file() {
    local file="$1"
    [[ -f "${file}" && -r "${file}" ]]
}

if is_valid_file "${path}"; then
    process_file "${path}"
fi
```

## Indentation & Formatting

- Use 2 spaces for indentation (no tabs).
- Maximum line length: 80 characters.
- Use `\` for line continuation.

```bash
long_command \
    --flag1 "value1" \
    --flag2 "value2" \
    --flag3 "value3"
```

## main() Pattern

```bash
#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    echo "Usage: $(basename "$0") [options] <input>"
    echo "Options:"
    echo "  -v, --verbose    Enable verbose output"
    echo "  -h, --help       Show this help"
}

main() {
    local verbose=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--verbose) verbose=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *) break ;;
        esac
    done

    if [[ $# -eq 0 ]]; then
        err "Missing required argument"
        usage
        exit 1
    fi

    # Script logic here
}

main "$@"
```
