# AlloyDB Omni Configuration

## Memory & CPU Tuning

### Docker Resource Limits

```bash
docker run -d \
    --name alloydb-omni \
    --cpus=4 \
    --memory=16g \
    --shm-size=256m \
    -e POSTGRES_PASSWORD=secret \
    -p 5432:5432 \
    -v alloydb-data:/var/lib/postgresql/data \
    google/alloydbomni:latest
```

### PostgreSQL Parameters

```sql
-- Connect and tune parameters
ALTER SYSTEM SET shared_buffers = '4GB';         -- 25% of container memory
ALTER SYSTEM SET effective_cache_size = '12GB';   -- 75% of container memory
ALTER SYSTEM SET work_mem = '64MB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET max_connections = 200;

-- Reload configuration
SELECT pg_reload_conf();

-- Verify settings
SHOW shared_buffers;
SELECT name, setting, unit, source FROM pg_settings WHERE source = 'configuration file';
```

### Kubernetes Resource Tuning

```yaml
apiVersion: alloydbomni.dbadmin.goog/v1
kind: DBCluster
metadata:
  name: production-cluster
spec:
  primarySpec:
    resources:
      cpu: "8"
      memory: "32Gi"
    parameters:
      shared_buffers: "8GB"
      effective_cache_size: "24GB"
      work_mem: "128MB"
      maintenance_work_mem: "2GB"
      max_connections: "500"
      random_page_cost: "1.1"
      effective_io_concurrency: "200"
```

## Persistence Volumes

### Docker Named Volumes

```bash
# Create volume with specific driver options
docker volume create \
    --driver local \
    --opt type=none \
    --opt device=/mnt/ssd/alloydb \
    --opt o=bind \
    alloydb-data
```

### Kubernetes PVC

```yaml
spec:
  primarySpec:
    persistence:
      size: 500Gi
      storageClass: premium-rwo  # SSD-backed storage
      accessModes:
        - ReadWriteOnce
```

## Networking

### Docker Networking

```bash
# Create a dedicated network
docker network create alloydb-net

# Run AlloyDB on the network
docker run -d \
    --name alloydb-omni \
    --network alloydb-net \
    -e POSTGRES_PASSWORD=secret \
    -v alloydb-data:/var/lib/postgresql/data \
    google/alloydbomni:latest

# Other containers connect by name
docker run --network alloydb-net myapp \
    -e DATABASE_URL="postgresql://postgres:secret@alloydb-omni:5432/mydb"
```

### SSL/TLS Configuration

```bash
# Mount custom SSL certificates
docker run -d \
    --name alloydb-omni \
    -e POSTGRES_PASSWORD=secret \
    -v alloydb-data:/var/lib/postgresql/data \
    -v ./certs/server.crt:/var/lib/postgresql/server.crt:ro \
    -v ./certs/server.key:/var/lib/postgresql/server.key:ro \
    -p 5432:5432 \
    google/alloydbomni:latest
```

```sql
-- Enable SSL in PostgreSQL config
ALTER SYSTEM SET ssl = 'on';
ALTER SYSTEM SET ssl_cert_file = '/var/lib/postgresql/server.crt';
ALTER SYSTEM SET ssl_key_file = '/var/lib/postgresql/server.key';
SELECT pg_reload_conf();
```

## Columnar Engine Configuration

```sql
-- Enable the columnar engine extension
CREATE EXTENSION IF NOT EXISTS google_columnar_engine;

-- Add tables/columns to columnar cache
SELECT google_columnar_engine_add('analytics_events');

-- Check columnar engine memory usage
SELECT * FROM g_columnar_memory_usage;

-- Configure memory limit for columnar engine
ALTER SYSTEM SET google_columnar_engine.memory_limit = '4GB';
SELECT pg_reload_conf();
```

## Logging

```sql
-- Configure query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
ALTER SYSTEM SET log_statement = 'ddl';              -- Log DDL statements
ALTER SYSTEM SET log_connections = 'on';
ALTER SYSTEM SET log_disconnections = 'on';
SELECT pg_reload_conf();
```

```bash
# View container logs
docker logs -f alloydb-omni

# Kubernetes logs
kubectl logs -f pod/my-omni-cluster-0
```

## Health Checks

```yaml
# docker-compose.yml health check
services:
  alloydb:
    image: google/alloydbomni:latest
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
```
