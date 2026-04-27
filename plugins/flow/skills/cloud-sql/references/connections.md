# Cloud SQL Connection Patterns

## GKE: Auth Proxy Sidecar

The recommended pattern for GKE workloads is to run the Cloud SQL Auth Proxy as a sidecar container. The application connects to `127.0.0.1` as if the database were local.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      serviceAccountName: my-app-ksa   # KSA bound to GSA via Workload Identity
      containers:
        - name: app
          image: gcr.io/my-project/my-app:latest
          env:
            - name: DB_HOST
              value: "127.0.0.1"
            - name: DB_PORT
              value: "5432"
            - name: DB_NAME
              value: "myapp"
          envFrom:
            - secretRef:
                name: db-credentials

        - name: cloud-sql-proxy
          image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2
          args:
            - "--structured-logs"
            - "--port=5432"
            - "MY_PROJECT:us-central1:my-postgres"
          securityContext:
            runAsNonRoot: true
          resources:
            requests:
              memory: "32Mi"
              cpu: "10m"
            limits:
              memory: "128Mi"
              cpu: "500m"
```

### Workload Identity binding

```bash
# Create GCP service account
gcloud iam service-accounts create my-app-gsa \
    --project=MY_PROJECT

# Grant Cloud SQL Client role
gcloud projects add-iam-policy-binding MY_PROJECT \
    --member="serviceAccount:my-app-gsa@MY_PROJECT.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

# Bind KSA → GSA
gcloud iam service-accounts add-iam-policy-binding my-app-gsa@MY_PROJECT.iam.gserviceaccount.com \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:MY_PROJECT.svc.id.goog[my-namespace/my-app-ksa]"

# Annotate the Kubernetes service account
kubectl annotate serviceaccount my-app-ksa \
    --namespace=my-namespace \
    iam.gke.io/gcp-service-account=my-app-gsa@MY_PROJECT.iam.gserviceaccount.com
```

---

## Cloud Run

### Auto-managed Unix socket (recommended)

Cloud Run natively manages the Auth Proxy — no sidecar needed. Add the instance connection name at deploy time and connect via Unix socket.

```bash
gcloud run deploy my-service \
    --image=gcr.io/my-project/my-app:latest \
    --region=us-central1 \
    --add-cloudsql-instances=MY_PROJECT:us-central1:my-postgres \
    --set-env-vars="DB_INSTANCE=MY_PROJECT:us-central1:my-postgres"
```

Application connection string (Unix socket):

```python
# PostgreSQL via psycopg
import os
INSTANCE = os.environ["DB_INSTANCE"]
DSN = f"postgresql://user:pass@/mydb?host=/cloudsql/{INSTANCE}"

# MySQL via PyMySQL
DSN = f"mysql+pymysql://user:pass@/mydb?unix_socket=/cloudsql/{INSTANCE}"
```

### Direct VPC connection (alternative)

For lower latency, connect via private IP over a Serverless VPC Access connector or Direct VPC Egress:

```bash
gcloud run deploy my-service \
    --image=gcr.io/my-project/my-app:latest \
    --region=us-central1 \
    --network=my-vpc \
    --subnet=my-subnet \
    --vpc-egress=private-ranges-only \
    --set-env-vars="DB_HOST=10.0.0.5,DB_PORT=5432"
```

---

## Compute Engine

### Auth Proxy binary (recommended)

```bash
# Download the proxy
curl -o cloud-sql-proxy \
    https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

# Run as a systemd service (see below) or in the foreground
./cloud-sql-proxy --port=5432 MY_PROJECT:us-central1:my-postgres
```

Systemd unit file at `/etc/systemd/system/cloud-sql-proxy.service`:

```ini
[Unit]
Description=Cloud SQL Auth Proxy
After=network.target

[Service]
Type=simple
User=nobody
ExecStart=/usr/local/bin/cloud-sql-proxy \
    --structured-logs \
    --port=5432 \
    MY_PROJECT:us-central1:my-postgres
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable --now cloud-sql-proxy
```

### Private IP via VPC (lowest latency)

If the VM is in the same VPC as the Cloud SQL instance, connect directly using the private IP — no proxy needed:

```bash
psql "host=10.0.0.5 port=5432 dbname=mydb user=postgres sslmode=require"
```

Grant the VM's service account `roles/cloudsql.client` to manage SSL certificates automatically.

---

## Local Development

```bash
# Install the proxy
curl -o cloud-sql-proxy \
    https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.14.1/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

# Authenticate with application default credentials
gcloud auth application-default login

# Start proxy (runs in foreground; use & or a separate terminal)
./cloud-sql-proxy MY_PROJECT:us-central1:my-postgres --port=5432

# Connect
psql "host=127.0.0.1 port=5432 dbname=mydb user=myuser"
```

For multiple instances on different ports:

```bash
./cloud-sql-proxy \
    "MY_PROJECT:us-central1:postgres-instance?port=5432" \
    "MY_PROJECT:us-central1:mysql-instance?port=3306"
```

---

## PSC (Private Service Connect)

PSC allows consuming Cloud SQL from another project or organization without VPC peering.

```bash
# 1. Enable PSC on the Cloud SQL instance
gcloud sql instances patch my-postgres \
    --enable-google-private-path \
    --no-assign-ip

# 2. Get the PSC service attachment URI (shown in instance describe)
gcloud sql instances describe my-postgres \
    --format="value(settings.ipConfiguration.pscConfig.serviceAttachmentLink)"
# Output: projects/SERVICE_PROJECT/.../serviceAttachments/...

# 3. Create PSC endpoint in the consumer project
gcloud compute addresses create psc-cloud-sql-ip \
    --region=us-central1 \
    --subnet=my-subnet

gcloud compute forwarding-rules create psc-cloud-sql \
    --region=us-central1 \
    --network=my-vpc \
    --address=psc-cloud-sql-ip \
    --target-service-attachment=projects/SERVICE_PROJECT/.../serviceAttachments/...

# 4. Configure DNS (Cloud DNS private zone)
gcloud dns managed-zones create cloud-sql-zone \
    --dns-name="sql.goog." \
    --visibility=private \
    --networks=my-vpc

gcloud dns record-sets create my-postgres.sql.goog. \
    --zone=cloud-sql-zone \
    --type=A \
    --ttl=300 \
    --rrdatas=PSC_ENDPOINT_IP
```

---

## Connection String Formats

| Engine | Format |
|---|---|
| PostgreSQL (via proxy) | `postgresql://user:pass@127.0.0.1:5432/dbname` |
| PostgreSQL (private IP) | `postgresql://user:pass@10.0.0.5:5432/dbname?sslmode=require` |
| PostgreSQL (Cloud Run socket) | `postgresql://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE` |
| MySQL (via proxy) | `mysql://user:pass@127.0.0.1:3306/dbname` |
| MySQL (Cloud Run socket) | `mysql://user:pass@/dbname?unix_socket=/cloudsql/PROJECT:REGION:INSTANCE` |
| SQL Server (via proxy) | `mssql://user:pass@127.0.0.1:1433/dbname` |

SQLAlchemy connection strings:

```python
# PostgreSQL + asyncpg
"postgresql+asyncpg://user:pass@127.0.0.1:5432/dbname"

# PostgreSQL + psycopg3
"postgresql+psycopg://user:pass@127.0.0.1:5432/dbname"

# MySQL + aiomysql
"mysql+aiomysql://user:pass@127.0.0.1:3306/dbname"

# SQL Server + aioodbc
"mssql+aioodbc://user:pass@127.0.0.1:1433/dbname?driver=ODBC+Driver+18+for+SQL+Server"
```

---

## Connection Pooling

### PgBouncer for PostgreSQL

Cloud SQL does not include a built-in connection pooler for PostgreSQL. For high-concurrency workloads, run PgBouncer in front of Cloud SQL.

```ini
# /etc/pgbouncer/pgbouncer.ini
[databases]
mydb = host=127.0.0.1 port=5432 dbname=mydb

[pgbouncer]
listen_port = 6432
listen_addr = 0.0.0.0
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction          ; use session mode for LISTEN/NOTIFY
max_client_conn = 1000
default_pool_size = 25
min_pool_size = 5
reserve_pool_size = 5
server_reset_query = DISCARD ALL
```

Recommended: run PgBouncer as a Cloud Run service or GKE deployment co-located with the Auth Proxy.

### ProxySQL for MySQL

```ini
# /etc/proxysql.cnf (minimal)
datadir="/var/lib/proxysql"

mysql_servers =
(
    { address="127.0.0.1", port=3306, hostgroup=0 }
)

mysql_users =
(
    { username="app", password="pass", default_hostgroup=0 }
)

mysql_variables =
{
    threads=4
    max_connections=2048
    default_query_timeout=36000000
    interfaces="0.0.0.0:6033"
}
```
