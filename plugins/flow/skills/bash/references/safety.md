# Defensive Bash Scripting

## Essential Safety Header

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
```

| Setting | Purpose |
|---------|---------|
| `set -e` | Exit immediately on non-zero return |
| `set -u` | Error on unset variables |
| `set -o pipefail` | Pipe returns rightmost non-zero exit code |
| `IFS=$'\n\t'` | Safer word splitting (no space splitting) |

## ShellCheck Compliance

Always run [ShellCheck](https://www.shellcheck.net/) on scripts:

```bash
# Install
apt-get install shellcheck  # Debian/Ubuntu
brew install shellcheck      # macOS

# Run
shellcheck myscript.sh

# Disable specific rules when justified
# shellcheck disable=SC2086
echo $unquoted_intentionally
```

### Common ShellCheck Fixes

```bash
# SC2086: Double quote to prevent globbing and word splitting
# Bad
files=$(ls *.txt)
# Good
files=( *.txt )

# SC2046: Quote command substitution
# Bad
rm $(find . -name "*.tmp")
# Good
find . -name "*.tmp" -delete

# SC2155: Declare and assign separately
# Bad
local output="$(command)"
# Good
local output
output="$(command)"

# SC2034: Variable appears unused (often false positive for exports)
# shellcheck disable=SC2034
readonly MY_CONST="value"
```

## Handling Spaces in Filenames

```bash
# Always quote variables
cp "${source}" "${dest}"

# Use arrays for file lists
local -a files
mapfile -t files < <(find . -name "*.txt")
for f in "${files[@]}"; do
    process "${f}"
done

# Use null-delimited output
find . -name "*.txt" -print0 | while IFS= read -r -d '' file; do
    process "${file}"
done

# Use -- to prevent option injection
rm -- "${filename}"
cp -- "${src}" "${dst}"
```

## Proper Exit Codes

```bash
# Standard exit codes
readonly EX_OK=0
readonly EX_USAGE=64       # Command line usage error
readonly EX_DATAERR=65     # Data format error
readonly EX_NOINPUT=66     # Cannot open input
readonly EX_SOFTWARE=70    # Internal software error
readonly EX_CANTCREAT=73   # Can't create output file
readonly EX_TEMPFAIL=75    # Temporary failure, retry

# Usage
main() {
    if [[ $# -eq 0 ]]; then
        echo "Usage: $(basename "$0") <file>" >&2
        exit "${EX_USAGE}"
    fi

    local input="$1"
    if [[ ! -f "${input}" ]]; then
        echo "Error: File not found: ${input}" >&2
        exit "${EX_NOINPUT}"
    fi
}
```

## Signal Handling

```bash
#!/usr/bin/env bash
set -euo pipefail

TEMP_DIR=""
CHILD_PID=""

cleanup() {
    local exit_code=$?
    # Kill child process if running
    if [[ -n "${CHILD_PID}" ]]; then
        kill "${CHILD_PID}" 2>/dev/null || true
        wait "${CHILD_PID}" 2>/dev/null || true
    fi
    # Remove temp files
    if [[ -n "${TEMP_DIR}" && -d "${TEMP_DIR}" ]]; then
        rm -rf "${TEMP_DIR}"
    fi
    exit "${exit_code}"
}

trap cleanup EXIT ERR
trap 'echo "Interrupted" >&2; exit 130' INT
trap 'echo "Terminated" >&2; exit 143' TERM

main() {
    TEMP_DIR="$(mktemp -d)"
    long_running_command &
    CHILD_PID=$!
    wait "${CHILD_PID}"
    CHILD_PID=""
}

main "$@"
```

## Avoiding Common Pitfalls

### Don't Parse ls

```bash
# Bad
for f in $(ls *.txt); do

# Good
for f in *.txt; do
    [[ -e "${f}" ]] || continue  # Handle no matches
```

### Don't Use eval

```bash
# Bad: security risk
eval "${user_input}"

# Good: use arrays for dynamic commands
local -a cmd=("curl" "-s" "-H" "Authorization: Bearer ${token}" "${url}")
"${cmd[@]}"
```

### Check Command Existence

```bash
require_command() {
    local cmd="$1"
    if ! command -v "${cmd}" &>/dev/null; then
        echo "Error: '${cmd}' is required but not installed." >&2
        exit 1
    fi
}

require_command jq
require_command curl
```

### Safe Temporary Files

```bash
# Always use mktemp
local tmp_file
tmp_file="$(mktemp)"

local tmp_dir
tmp_dir="$(mktemp -d)"

# Never use predictable names in /tmp (symlink attacks)
# Bad: /tmp/myapp.log
```

### Arithmetic Safety

```bash
# Use (( )) for arithmetic, not expr
(( count++ ))
(( total = a + b ))

if (( count > max )); then
    echo "Exceeded maximum"
fi

# Integer validation
is_integer() {
    local value="$1"
    [[ "${value}" =~ ^-?[0-9]+$ ]]
}
```

### Subshell Variable Scope

```bash
# Bug: variable set in pipe subshell is lost
count=0
echo -e "a\nb\nc" | while read -r line; do
    (( count++ ))  # This modifies count in subshell
done
echo "${count}"  # Still 0!

# Fix: use process substitution
count=0
while read -r line; do
    (( count++ ))
done < <(echo -e "a\nb\nc")
echo "${count}"  # 3
```

## Logging Pattern

```bash
readonly LOG_LEVEL="${LOG_LEVEL:-INFO}"

log() {
    local level="$1"; shift
    local timestamp
    timestamp="$(date +'%Y-%m-%d %H:%M:%S')"
    echo "[${timestamp}] [${level}] $*" >&2
}

log_debug() { [[ "${LOG_LEVEL}" == "DEBUG" ]] && log "DEBUG" "$@" || true; }
log_info()  { log "INFO" "$@"; }
log_warn()  { log "WARN" "$@"; }
log_error() { log "ERROR" "$@"; }

# Usage
log_info "Starting process"
log_error "Failed to connect to ${host}"
```

## Retry Pattern

```bash
retry() {
    local max_attempts="$1"; shift
    local delay="$1"; shift
    local attempt=1

    while (( attempt <= max_attempts )); do
        if "$@"; then
            return 0
        fi
        log_warn "Attempt ${attempt}/${max_attempts} failed. Retrying in ${delay}s..."
        sleep "${delay}"
        (( attempt++ ))
    done

    log_error "All ${max_attempts} attempts failed"
    return 1
}

# Usage
retry 3 5 curl -sf "https://api.example.com/health"
```
