# Common Bash Patterns

## Argument Parsing with getopts

```bash
#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<EOF
Usage: $(basename "$0") [-v] [-o output] [-n count] input_file

Options:
  -v          Verbose mode
  -o FILE     Output file (default: stdout)
  -n COUNT    Number of iterations (default: 1)
  -h          Show this help
EOF
}

main() {
    local verbose=false
    local output="/dev/stdout"
    local count=1

    while getopts ":vo:n:h" opt; do
        case "${opt}" in
            v) verbose=true ;;
            o) output="${OPTARG}" ;;
            n) count="${OPTARG}" ;;
            h) usage; exit 0 ;;
            :) echo "Error: -${OPTARG} requires an argument" >&2; exit 1 ;;
            ?) echo "Error: Unknown option -${OPTARG}" >&2; exit 1 ;;
        esac
    done
    shift $((OPTIND - 1))

    if [[ $# -eq 0 ]]; then
        echo "Error: input_file required" >&2
        usage >&2
        exit 1
    fi

    local input_file="$1"
    # ... use ${verbose}, ${output}, ${count}, ${input_file}
}

main "$@"
```

## Long Options (Manual Parsing)

```bash
main() {
    local verbose=false
    local output=""
    local dry_run=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v|--verbose)   verbose=true; shift ;;
            -o|--output)    output="$2"; shift 2 ;;
            --dry-run)      dry_run=true; shift ;;
            -h|--help)      usage; exit 0 ;;
            --)             shift; break ;;
            -*)             echo "Unknown option: $1" >&2; exit 1 ;;
            *)              break ;;
        esac
    done

    local -a positional=("$@")
    # ...
}
```

## Trap for Cleanup

```bash
cleanup() {
    local exit_code=$?
    rm -rf "${TEMP_DIR:-}"
    exit "${exit_code}"
}

main() {
    trap cleanup EXIT

    TEMP_DIR="$(mktemp -d)"
    # Work in TEMP_DIR; cleanup runs automatically on exit
    cp important_file "${TEMP_DIR}/"
    process "${TEMP_DIR}/important_file"
}
```

## Here-Documents

```bash
# Standard here-doc
cat <<EOF
Hello, ${name}!
Today is $(date).
EOF

# No variable expansion (quoted delimiter)
cat <<'EOF'
This is literal: ${not_expanded}
Also literal: $(not_executed)
EOF

# Indented here-doc (tabs stripped with <<-)
if true; then
 cat <<-EOF
 Indented content.
 Tabs are stripped.
 EOF
fi

# Here-string
grep "pattern" <<< "${my_string}"
```

## Process Substitution

```bash
# Diff two command outputs
diff <(sort file1.txt) <(sort file2.txt)

# Read from multiple sources
paste <(cut -f1 data.tsv) <(cut -f3 data.tsv)

# Feed command output as a file argument
while IFS= read -r line; do
    echo "Processing: ${line}"
done < <(find /path -name "*.txt" -print0 | xargs -0 -I{} basename {})
```

## Array Manipulation

```bash
# Declare array
local -a fruits=("apple" "banana" "cherry")

# Append
fruits+=("date" "elderberry")

# Length
echo "Count: ${#fruits[@]}"

# Iterate
for fruit in "${fruits[@]}"; do
    echo "${fruit}"
done

# Slice (offset:length)
echo "${fruits[@]:1:2}"  # banana cherry

# Check if element exists
if [[ " ${fruits[*]} " == *" banana "* ]]; then
    echo "Found banana"
fi

# Index access
echo "First: ${fruits[0]}"
echo "Last: ${fruits[-1]}"

# Remove element by index
unset 'fruits[1]'
# Re-index after removal
fruits=("${fruits[@]}")
```

## Associative Arrays

```bash
# Declare (must use declare -A)
declare -A config
config[host]="localhost"
config[port]="5432"
config[db]="myapp"

# Or inline
declare -A colors=(
    [red]="#FF0000"
    [green]="#00FF00"
    [blue]="#0000FF"
)

# Access
echo "Host: ${config[host]}"

# Keys
echo "Keys: ${!config[@]}"

# Iterate
for key in "${!config[@]}"; do
    echo "${key}=${config[${key}]}"
done

# Check key exists
if [[ -v config[host] ]]; then
    echo "host is set"
fi
```

## Reading Files Line by Line

```bash
# Standard pattern
while IFS= read -r line; do
    echo "Line: ${line}"
done < input.txt

# Process command output
while IFS= read -r line; do
    echo "${line}"
done < <(some_command)

# Read CSV/TSV
while IFS=',' read -r name age city; do
    echo "${name} is ${age} years old from ${city}"
done < data.csv

# Read with null delimiter (for filenames with spaces)
while IFS= read -r -d '' file; do
    echo "File: ${file}"
done < <(find . -name "*.txt" -print0)
```

## String Manipulation

```bash
str="Hello, World!"

# Substring: ${var:offset:length}
echo "${str:0:5}"     # Hello

# Replace first: ${var/pattern/replacement}
echo "${str/World/Bash}"  # Hello, Bash!

# Replace all: ${var//pattern/replacement}
path="/a/b/c/d"
echo "${path//\//-}"  # -a-b-c-d

# Remove prefix: ${var#pattern} (shortest) ${var##pattern} (longest)
file="/path/to/script.sh"
echo "${file##*/}"    # script.sh (basename)

# Remove suffix: ${var%pattern} (shortest) ${var%%pattern} (longest)
echo "${file%/*}"     # /path/to (dirname)
echo "${file%.sh}"    # /path/to/script

# Uppercase/lowercase
echo "${str^^}"       # HELLO, WORLD!
echo "${str,,}"       # hello, world!

# Default value
echo "${unset_var:-default}"    # Use default if unset
echo "${unset_var:=default}"    # Set and use default if unset
```

## Parallel Execution

```bash
# Background jobs with wait
for url in "${urls[@]}"; do
    curl -sO "${url}" &
done
wait  # Wait for all background jobs

# xargs parallel
find . -name "*.jpg" -print0 | xargs -0 -P4 -I{} convert {} -resize 800x600 resized/{}

# GNU parallel (if available)
parallel -j4 convert {} -resize 800x600 resized/{} ::: *.jpg
```
