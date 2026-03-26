# Migration to AlloyDB

## From Cloud SQL for PostgreSQL

### Using Database Migration Service (DMS)

```bash
# 1. Create a connection profile for source Cloud SQL
gcloud database-migration connection-profiles create cloudsql-source \
    --region=us-central1 \
    --display-name="Cloud SQL Source" \
    --provider=CLOUDSQL \
    --cloudsql-instance=my-project:us-central1:my-cloudsql

# 2. Create a connection profile for AlloyDB destination
gcloud database-migration connection-profiles create alloydb-dest \
    --region=us-central1 \
    --display-name="AlloyDB Dest" \
    --provider=ALLOYDB \
    --alloydb-cluster=my-alloydb-cluster

# 3. Create migration job
gcloud database-migration migration-jobs create cloudsql-to-alloydb \
    --region=us-central1 \
    --type=CONTINUOUS \
    --source=cloudsql-source \
    --destination=alloydb-dest
```

### Using pg_dump/pg_restore

```bash
# Export from Cloud SQL
gcloud sql export sql my-cloudsql-instance gs://my-bucket/export.sql \
    --database=mydb

# Or use pg_dump directly (via Cloud SQL Auth Proxy)
pg_dump -Fc -j4 -d mydb -h 127.0.0.1 -U postgres -f mydb.dump

# Import to AlloyDB
pg_restore -j4 -d mydb -h ALLOYDB_IP -U postgres mydb.dump
```

## From On-Premises PostgreSQL

### Using DMS with Reverse SSH Tunnel

```bash
# 1. Create source connection profile with SSH tunnel
gcloud database-migration connection-profiles create onprem-source \
    --region=us-central1 \
    --display-name="On-Prem PG" \
    --provider=POSTGRESQL \
    --host=10.0.0.50 \
    --port=5432 \
    --username=replicator \
    --password=secret \
    --forward-ssh-hostname=bastion.example.com \
    --forward-ssh-username=tunnel-user \
    --forward-ssh-private-key-file=~/.ssh/id_rsa

# 2. Create migration job with continuous replication
gcloud database-migration migration-jobs create onprem-to-alloydb \
    --region=us-central1 \
    --type=CONTINUOUS \
    --source=onprem-source \
    --destination=alloydb-dest
```

### Prerequisites for Logical Replication

On the source PostgreSQL server:

```ini
# postgresql.conf
wal_level = logical
max_replication_slots = 10
max_wal_senders = 10
```

```sql
-- Create replication user
CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'secret';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO replicator;

-- Create publication
CREATE PUBLICATION dms_pub FOR ALL TABLES;
```

## Migration Checklist

1. **Pre-migration**
   - Inventory extensions (`SELECT * FROM pg_extension`)
   - Verify extension compatibility with AlloyDB
   - Check for unsupported features (e.g., certain procedural languages)
   - Benchmark current workload for comparison

2. **Schema migration**
   - Export schema: `pg_dump --schema-only -d mydb -f schema.sql`
   - Review and adjust for AlloyDB (e.g., enable columnar engine on analytics tables)

3. **Data migration**
   - Use DMS for minimal downtime (continuous replication)
   - Or pg_dump/pg_restore for simpler one-time migration

4. **Validation**
   - Row count comparison
   - Checksum verification on critical tables
   - Run application test suite against AlloyDB
   - Performance benchmarking (pgbench, custom workloads)

5. **Cutover**
   - Stop writes to source
   - Wait for replication lag to reach zero
   - Promote AlloyDB as primary
   - Update application connection strings
   - Monitor for errors

## Extension Compatibility

AlloyDB supports most common PostgreSQL extensions:

```sql
-- Check available extensions
SELECT * FROM pg_available_extensions ORDER BY name;

-- Commonly used extensions supported by AlloyDB:
-- pgvector, pg_trgm, hstore, uuid-ossp, pg_stat_statements,
-- postgis, pgcrypto, pg_cron, google_ml_integration
```
