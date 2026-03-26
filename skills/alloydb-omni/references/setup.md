# AlloyDB Omni Setup & Deployment

## Docker Deployment

```bash
# Pull the AlloyDB Omni image
docker pull google/alloydbomni:latest

# Run with persistent storage
docker run -d \
    --name alloydb-omni \
    -e POSTGRES_PASSWORD=mysecretpassword \
    -p 5432:5432 \
    -v alloydb-data:/var/lib/postgresql/data \
    google/alloydbomni:latest

# Connect
psql -h localhost -U postgres
```

### Docker Compose

```yaml
# docker-compose.yml
services:
  alloydb:
    image: google/alloydbomni:latest
    container_name: alloydb-omni
    environment:
      POSTGRES_PASSWORD: mysecretpassword
      POSTGRES_DB: myapp
      POSTGRES_USER: postgres
    ports:
      - "5432:5432"
    volumes:
      - alloydb-data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    restart: unless-stopped
    shm_size: '256m'

volumes:
  alloydb-data:
```

## Podman Deployment

```bash
# Run with Podman (rootless)
podman run -d \
    --name alloydb-omni \
    -e POSTGRES_PASSWORD=mysecretpassword \
    -p 5432:5432 \
    -v alloydb-data:/var/lib/postgresql/data:Z \
    google/alloydbomni:latest
```

## RPM Installation (Bare Metal / VM)

For RHEL, CentOS, Rocky Linux, or Oracle Linux deployments without containers.

```bash
# Add the AlloyDB Omni repository
sudo tee /etc/yum.repos.d/alloydb-omni.repo << 'EOF'
[alloydb-omni]
name=AlloyDB Omni
baseurl=https://storage.googleapis.com/alloydb-omni-yum/
enabled=1
gpgcheck=0
EOF

# Install AlloyDB Omni
sudo yum install -y alloydbomni

# Initialize the database cluster
sudo alloydb-omni init --data-dir=/var/lib/alloydb/data

# Start the service
sudo systemctl enable --now alloydb-omni

# Verify
sudo systemctl status alloydb-omni
psql -h localhost -U postgres
```

### RPM Configuration

```bash
# Configuration file location
/var/lib/alloydb/data/postgresql.conf

# Key settings to tune after install
sudo -u postgres psql -c "ALTER SYSTEM SET shared_buffers = '4GB';"
sudo -u postgres psql -c "ALTER SYSTEM SET effective_cache_size = '12GB';"
sudo -u postgres psql -c "ALTER SYSTEM SET work_mem = '64MB';"
sudo -u postgres psql -c "ALTER SYSTEM SET maintenance_work_mem = '1GB';"

# Restart to apply
sudo systemctl restart alloydb-omni

# Enable extensions
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS google_columnar_engine;"
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Upgrading RPM Installation

```bash
# Check current version
psql -h localhost -U postgres -c "SELECT version();"

# Update package
sudo yum update -y alloydbomni

# Restart
sudo systemctl restart alloydb-omni
```

## Kubernetes Operator

### Prerequisites

- Kubernetes 1.25+ cluster (GKE Autopilot, standard GKE, EKS, AKS, or on-prem)
- `kubectl` configured with cluster admin access
- cert-manager installed (the operator depends on it for webhook TLS)

```bash
# Install cert-manager if not present
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
kubectl wait --for=condition=available --timeout=120s \
    deployment/cert-manager -n cert-manager
```

### Install the Operator

```bash
# Install the AlloyDB Omni Kubernetes operator
kubectl apply -f https://storage.googleapis.com/alloydb-omni-operator/latest/alloydb-omni-operator.yaml

# Wait for operator to be ready
kubectl wait --for=condition=available --timeout=120s \
    deployment/alloydb-omni-operator -n alloydb-omni-system

# Verify CRDs are registered
kubectl get crd | grep alloydbomni
# Expected: dbclusters.alloydbomni.dbadmin.goog
```

### DBCluster Custom Resource

```yaml
# alloydb-cluster.yaml
apiVersion: alloydbomni.dbadmin.goog/v1
kind: DBCluster
metadata:
  name: my-omni-cluster
  namespace: database
spec:
  databaseVersion: "15"
  primarySpec:
    adminUser:
      passwordRef:
        name: db-password-secret
    resources:
      cpu: "4"
      memory: "16Gi"
    parameters:
      max_connections: "200"
      shared_buffers: "4GB"
      work_mem: "64MB"
    availabilityOptions:
      livenessProbe: Enabled
    persistence:
      size: 100Gi
      storageClass: standard-rwo
  # Optional: read pool for scaling reads
  readPoolSpec:
    replicas: 2
    resources:
      cpu: "2"
      memory: "8Gi"
---
apiVersion: v1
kind: Secret
metadata:
  name: db-password-secret
  namespace: database
type: Opaque
stringData:
  db-password: mysecretpassword
```

```bash
# Create namespace and apply
kubectl create namespace database
kubectl apply -f alloydb-cluster.yaml

# Check status
kubectl get dbclusters -n database
kubectl describe dbcluster my-omni-cluster -n database

# Watch for readiness
kubectl wait --for=condition=Ready --timeout=300s \
    dbcluster/my-omni-cluster -n database
```

### Connecting to the Operator-Managed Cluster

```bash
# Get the connection service
kubectl get svc -n database | grep my-omni-cluster

# Port-forward for local access
kubectl port-forward svc/my-omni-cluster-rw -n database 5432:5432

# Connect
PGPASSWORD=mysecretpassword psql -h localhost -U postgres
```

### Operator Lifecycle Management

```bash
# Scale read replicas
kubectl patch dbcluster my-omni-cluster -n database \
    --type=merge -p '{"spec":{"readPoolSpec":{"replicas":3}}}'

# Update parameters (rolling restart)
kubectl patch dbcluster my-omni-cluster -n database \
    --type=merge -p '{"spec":{"primarySpec":{"parameters":{"max_connections":"300"}}}}'

# Check operator logs
kubectl logs -n alloydb-omni-system deployment/alloydb-omni-operator -f

# Backup (if backup configuration is set)
kubectl annotate dbcluster my-omni-cluster -n database \
    alloydbomni.dbadmin.goog/backup=true

# Delete cluster (data persists in PVC)
kubectl delete dbcluster my-omni-cluster -n database
```

### High Availability with Operator

```yaml
# HA configuration with automatic failover
apiVersion: alloydbomni.dbadmin.goog/v1
kind: DBCluster
metadata:
  name: ha-cluster
spec:
  databaseVersion: "15"
  primarySpec:
    adminUser:
      passwordRef:
        name: db-password-secret
    resources:
      cpu: "4"
      memory: "16Gi"
    availabilityOptions:
      livenessProbe: Enabled
      standby: Enabled
    persistence:
      size: 200Gi
      storageClass: standard-rwo
  readPoolSpec:
    replicas: 2
    resources:
      cpu: "2"
      memory: "8Gi"
```

## Local Development Workflow

```bash
# Quick start for local dev
docker run -d \
    --name alloydb-dev \
    -e POSTGRES_PASSWORD=dev \
    -e POSTGRES_DB=myapp_dev \
    -p 5432:5432 \
    -v alloydb-dev-data:/var/lib/postgresql/data \
    google/alloydbomni:latest

# Load initial schema
psql -h localhost -U postgres -d myapp_dev -f schema.sql

# Run application tests
DATABASE_URL="postgresql://postgres:dev@localhost:5432/myapp_dev" make test
```

### Initialization Scripts

Place `.sql` or `.sh` files in `/docker-entrypoint-initdb.d/` to run on first start:

```sql
-- init-scripts/01-extensions.sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS google_columnar_engine;

-- init-scripts/02-schema.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Upgrading

```bash
# Pull the latest image
docker pull google/alloydbomni:latest

# Stop and remove old container (data is in the volume)
docker stop alloydb-omni && docker rm alloydb-omni

# Start with new image
docker run -d \
    --name alloydb-omni \
    -e POSTGRES_PASSWORD=mysecretpassword \
    -p 5432:5432 \
    -v alloydb-data:/var/lib/postgresql/data \
    google/alloydbomni:latest
```
