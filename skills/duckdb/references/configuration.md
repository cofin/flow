# DuckDB Configuration & Administration

## Pragmas

```sql
-- Database file size and metadata
PRAGMA database_size;

-- DuckDB version
PRAGMA version;

-- Storage layout details per column (compression, row groups, byte sizes)
PRAGMA storage_info('my_table');

-- Table schema info (column names, types, nullability, defaults)
PRAGMA table_info('my_table');

-- Show all tables
PRAGMA show_tables;

-- Show detailed table information
PRAGMA show_tables_expanded;

-- Platform and build info
PRAGMA platform;
```

---

## SET Statements

```sql
-- Memory limit (default: 80% of system RAM)
SET memory_limit = '8GB';

-- Number of threads (default: number of CPU cores)
SET threads = 4;

-- Temp directory for spilling when memory is exceeded
SET temp_directory = '/tmp/duckdb_spill';

-- Default sort order
SET default_order = 'ASC';    -- or 'DESC'

-- Null ordering
SET default_null_order = 'NULLS LAST';  -- or 'NULLS FIRST'

-- Progress bar for long queries
SET enable_progress_bar = true;
SET enable_progress_bar_print = true;

-- Preserve insertion order (disable for faster aggregation)
SET preserve_insertion_order = false;

-- Timezone
SET TimeZone = 'America/New_York';

-- Query all current settings
SELECT * FROM duckdb_settings();

-- Get a specific setting
SELECT current_setting('memory_limit');
SELECT current_setting('threads');
```

---

## Database Files

### .duckdb Format

- DuckDB uses a single file (`.duckdb`) for persistent storage
- Write-Ahead Log (WAL) is stored alongside as `.duckdb.wal`
- Automatically checkpoints WAL into the main file periodically

### Checkpointing

```sql
-- Force a checkpoint (flush WAL to main database file)
CHECKPOINT;

-- Force checkpoint and truncate WAL
FORCE CHECKPOINT;

-- Configure automatic checkpoint threshold (bytes of WAL before auto-checkpoint)
SET wal_autocheckpoint = '256MB';
```

### File Locking

- Only one process can write to a `.duckdb` file at a time
- Multiple read-only connections are allowed
- Use `read_only=True` / `-readonly` for concurrent read access

```sql
-- Open read-only from CLI
-- duckdb -readonly my.duckdb
```

---

## Catalog: Inspecting the Database

### information_schema (SQL Standard)

```sql
-- All tables
SELECT table_schema, table_name, table_type
FROM information_schema.tables;

-- All columns for a table
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'my_table';

-- All schemata
SELECT * FROM information_schema.schemata;
```

### DuckDB System Functions

```sql
-- Tables with detailed metadata
SELECT * FROM duckdb_tables();

-- Columns
SELECT * FROM duckdb_columns() WHERE table_name = 'my_table';

-- Views
SELECT * FROM duckdb_views();

-- Indexes
SELECT * FROM duckdb_indexes();

-- Types (enums, structs, etc.)
SELECT * FROM duckdb_types();

-- Dependencies between objects
SELECT * FROM duckdb_dependencies();

-- Currently running queries
SELECT * FROM duckdb_temporary_files();

-- Attached databases
SELECT * FROM duckdb_databases();

-- Schemas
SELECT * FROM duckdb_schemas();

-- Functions (built-in and UDFs)
SELECT DISTINCT function_name FROM duckdb_functions()
WHERE function_name LIKE 'list_%';

-- Sequences
SELECT * FROM duckdb_sequences();

-- Constraints
SELECT * FROM duckdb_constraints() WHERE table_name = 'my_table';
```

---

## Extension Management

### Install and Load

```sql
-- Install an extension (downloads once)
INSTALL httpfs;

-- Load an extension (needed per session)
LOAD httpfs;

-- Install and load in one step (auto-loads on first use in some cases)
INSTALL httpfs;
LOAD httpfs;

-- List installed extensions
SELECT * FROM duckdb_extensions();

-- Check loaded vs installed
SELECT extension_name, installed, loaded FROM duckdb_extensions();
```

### Auto-Install and Auto-Load

Many core extensions auto-install and auto-load when first referenced:

```sql
-- httpfs auto-loads when accessing s3:// or https:// URLs
SELECT * FROM read_parquet('s3://bucket/data.parquet');

-- json auto-loads for read_json
SELECT * FROM read_json('data.json');
```

### Custom Extension Repositories

```sql
-- Use a custom repository
SET custom_extension_repository = 'https://my-extensions.example.com';
INSTALL my_custom_extension;
LOAD my_custom_extension;

-- Install from community repository
INSTALL spatial FROM community;
```

### Updating Extensions

```sql
-- Update all extensions
UPDATE EXTENSIONS;

-- Force reinstall a specific extension
FORCE INSTALL httpfs;
```

---

## Cloud Access Configuration

### httpfs (S3, GCS, HTTP)

```sql
INSTALL httpfs;
LOAD httpfs;

-- S3 credentials via SET
SET s3_region = 'us-east-1';
SET s3_access_key_id = 'AKIA...';
SET s3_secret_access_key = '...';

-- Or use secrets manager (preferred)
CREATE SECRET my_s3 (
    TYPE s3,
    KEY_ID 'AKIA...',
    SECRET '...',
    REGION 'us-east-1'
);
```

### AWS Credential Chain

```sql
-- Use default AWS credential chain (env vars, ~/.aws/credentials, instance profile)
CREATE SECRET aws_creds (
    TYPE s3,
    PROVIDER credential_chain
);
```

### GCS

```sql
-- GCS via S3-compatible endpoint
SET s3_endpoint = 'storage.googleapis.com';

-- Or use GCS secret
CREATE SECRET gcs_creds (
    TYPE gcs,
    KEY_ID '...',
    SECRET '...'
);
```

### Azure Blob Storage

```sql
-- Azure connection string
CREATE SECRET azure_creds (
    TYPE azure,
    CONNECTION_STRING 'DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;'
);
```

---

## Startup Configuration: .duckdbrc

DuckDB reads `~/.duckdbrc` on CLI startup (similar to `.bashrc`).

```sql
-- ~/.duckdbrc example
.timer on
SET memory_limit = '4GB';
SET threads = 4;
SET temp_directory = '/tmp/duckdb_spill';
LOAD httpfs;
.mode markdown
```

- Each line is executed as a SQL statement or dot-command
- Only applies to CLI sessions, not programmatic connections
- Use `.duckdbrc` for personal defaults (output mode, memory, extensions)

---

## Official Documentation

- Configuration: <https://duckdb.org/docs/configuration/overview>
- Pragmas: <https://duckdb.org/docs/configuration/pragmas>
- Extensions: <https://duckdb.org/docs/extensions/overview>
- Secrets manager: <https://duckdb.org/docs/configuration/secrets_manager>
- information_schema: <https://duckdb.org/docs/sql/information_schema>
- System catalog: <https://duckdb.org/docs/sql/duckdb_table_functions>
