# DuckDB CLI

## Interactive Shell

```bash
# Start interactive shell (in-memory)
duckdb

# Open or create a persistent database
duckdb my_database.duckdb

# Read-only mode
duckdb -readonly my_database.duckdb

# Execute a query and exit
duckdb -c "SELECT 'hello, duckdb'"
duckdb my.duckdb "SELECT COUNT(*) FROM my_table"
```

---

## Dot-Commands

```text
.help              -- Show all dot-commands
.mode              -- Set output mode (csv, json, markdown, table, line, etc.)
.headers on|off    -- Toggle column headers
.output FILE       -- Redirect output to a file
.output            -- Reset output to stdout
.read FILE         -- Execute SQL from a file
.tables            -- List tables
.schema TABLE      -- Show CREATE statement for a table
.timer on|off      -- Toggle query timer
.width N1 N2 ...   -- Set column widths for column mode
.quit              -- Exit the shell
```

### Output Modes

```text
.mode csv          -- Comma-separated values
.mode json         -- JSON array of objects
.mode markdown     -- Markdown table
.mode table        -- ASCII table (default)
.mode line         -- One value per line
.mode latex        -- LaTeX tabular
```

---

## Scripting and Piping

### Read SQL from a File

```bash
duckdb my.duckdb < queries.sql
duckdb my.duckdb ".read queries.sql"
```

### Read from stdin

```bash
echo "SELECT 42 AS answer;" | duckdb
cat data.csv | duckdb -c "SELECT * FROM read_csv('/dev/stdin')"
```

### Output Formatting for Scripts

```bash
# CSV output
duckdb -csv -c "SELECT 1 AS a, 2 AS b"

# JSON output
duckdb -json -c "SELECT 1 AS a, 2 AS b"

# No headers
duckdb -noheader -c "SELECT 42"

# Combine flags
duckdb -csv -noheader my.duckdb "SELECT name FROM users"
```

### Common One-Liners

```bash
# Convert CSV to Parquet
duckdb -c "COPY (SELECT * FROM read_csv('input.csv')) TO 'output.parquet' (FORMAT PARQUET)"

# Query remote Parquet
duckdb -c "INSTALL httpfs; LOAD httpfs; SELECT COUNT(*) FROM read_parquet('https://example.com/data.parquet')"

# Summarize a CSV
duckdb -c "SUMMARIZE SELECT * FROM read_csv('data.csv')"

# Describe schema
duckdb -c "DESCRIBE SELECT * FROM read_parquet('data.parquet')"
```

---

## Official Documentation

- CLI overview: <https://duckdb.org/docs/api/cli/overview>
- Dot-commands: <https://duckdb.org/docs/api/cli/dot_commands>
- Output formats: <https://duckdb.org/docs/api/cli/output_formats>
