# GCP Scripting Guide: BigQuery & GCS (2026 Edition)

This document outlines best practices for automating Google Cloud Platform tasks using `gcloud` and `bq` CLIs, focusing on data engineering workflows.

## 1. General Principles

*   **Service Accounts**: Always use Service Accounts (SA) for non-interactive scripts. Set `GOOGLE_APPLICATION_CREDENTIALS`.
*   **Project Explicit**: Always specify `--project_id` or set it via `gcloud config set` to avoid operating on the wrong environment.
*   **Format JSON**: Parse output using `--format=json` and `jq`. Never parse text output.

## 2. BigQuery (`bq`)

### 2.1. Safety & Optimization
*   **Dry Runs**: Always validate queries/costs before execution in scripts.
    ```bash
    bq query --use_legacy_sql=false --dry_run < query.sql
    ```
*   **Parameterized Queries**: PREVENT SQL INJECTION. Use `--parameter`.
    ```bash
    bq query --use_legacy_sql=false \
      --parameter='user_id:INT64:12345' \
      --parameter='status:STRING:active' \
      'SELECT * FROM `dataset.table` WHERE id = @user_id AND status = @status'
    ```

### 2.2. Batch Loading
Don't use `INSERT` statements for large data. Use `bq load`.
```bash
# Load NDJSON (Newlines Delimited JSON) - highly recommended over CSV
bq load --source_format=NEWLINE_DELIMITED_JSON \
   --autodetect \
   dataset.table \
   gs://my-bucket/data.json
```

### 2.3. Scripting Labels
Apply labels to jobs for cost tracking.
```bash
bq query --label=environment:prod --label=pipeline:etl_daily ...
```

## 3. Cloud Storage (`gcloud storage`)

**Note**: `gsutil` is legacy. Use `gcloud storage` (released 2022/2023) for significantly faster performance and modern API support.

### 3.1. High-Performance Transfers
`gcloud storage` automatically optimizes parallelization.

```bash
# Sync directory (like rsync)
gcloud storage rsync -r ./local_dir gs://my-bucket/remote_dir

# Parallel Copy
gcloud storage cp -r ./large_dataset gs://my-bucket/backup
```

### 3.2. Integrity Checks
Always verify checksums for critical data transfers.
```bash
# gcloud storage does CRC32c validation by default on download.
# To explicit check:
gcloud storage ls --json gs://my-bucket/file.txt | jq -r '.[0].crc32c'
```

### 3.3. Lifecycle Management
Script bucket configuration using JSON.
```bash
gcloud storage buckets update gs://my-bucket --lifecycle-file=lifecycle.json
```

## 4. Auth & Configuration in Scripts

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1. Activate Service Account
gcloud auth activate-service-account --key-file="$KEY_FILE"

# 2. Set Context
export CLOUDSDK_CORE_PROJECT="my-project-id"
export CLOUDSDK_CORE_DISABLE_PROMPTS=1 # Critical for automation

# 3. Execute
gcloud storage ls
```

## 5. Common Anti-Patterns

1.  **Using `gsutil`**: It is slower and less consistent with the rest of the `gcloud` ecosystem. Upgrade to `gcloud storage`.
2.  **Hardcoded Project IDs**: Pass project IDs as arguments or environment variables.
3.  **Parsing "Box Art"**: Don't grep the text table output of `gcloud`. Use `--format="value(field)"` or `--format=json`.

