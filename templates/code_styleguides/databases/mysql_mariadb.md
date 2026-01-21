# MySQL & MariaDB Scripting Guide (2026 Edition)

Best practices for scripting interactions with MySQL and MariaDB databases.

## 1. Connection Security

*   **Avoid Password in Command**: `mysql -u user -psecret` is insecure (visible in `ps`).
*   **Use Option Files**: Create a temporary `.my.cnf` file with restricted permissions (0600).
    ```ini
    [client]
    user=my_user
    password=my_secret
    host=127.0.0.1
    ```
*   **Invocation**:
    ```bash
    mysql --defaults-extra-file=/tmp/secure_config.cnf ...
    ```

## 2. Safety Flags

Always use these flags for batch scripts to prevent disasters.

```bash
# --safe-updates : Refuses UPDATE/DELETE without WHERE clauses using keys.
# --abort-source-on-error : Stop script execution if a query fails (like set -e).
# --batch : Tab-separated output (no ASCII tables).
# --raw : Don't escape special characters in output (good for piping).

mysql --defaults-extra-file=config.cnf \
      --safe-updates \
      --abort-source-on-error \
      --batch \
      --execute="source schema.sql;"
```

## 3. Import/Export

*   **mysqldump**: Use `--single-transaction` for InnoDB to ensure consistent non-locking backups.
    ```bash
    mysqldump --defaults-extra-file=config.cnf --single-transaction --quick --all-databases > dump.sql
    ```
*   **Loading Data**: Use `LOAD DATA LOCAL INFILE` for bulk loads (much faster than INSERTs). Ensure `local-infile=1` is enabled on client/server if needed.

## 4. Error Handling

Check exit codes immediately. MySQL client returns 0 on success, non-zero on error.

```bash
mysql ... < script.sql
if [[ $? -ne 0 ]]
  echo "Database migration failed!" >&2
  exit 1
fi
```
