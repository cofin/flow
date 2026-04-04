# Cloud SQL on GKE

Production patterns for connecting GKE workloads to Cloud SQL using the Auth Proxy sidecar and Workload Identity.

## Architecture

The Cloud SQL Auth Proxy runs as a **sidecar container** in the same Pod. The proxy handles authentication (via Workload Identity) and TLS, and exposes Cloud SQL on `localhost:5432` (Postgres) or `localhost:3306` (MySQL).

```
Pod
├── app-container  →  localhost:5432  →  cloud-sql-proxy  →  Cloud SQL (via proxy API)
└── cloud-sql-proxy (sidecar)
```

## Auth Proxy Sidecar Container Spec

```yaml
- name: cloud-sql-proxy
  image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.11.0
  args:
    - "--structured-logs"
    - "--port=5432"
    - "PROJECT_ID:REGION:INSTANCE_NAME"   # instance connection name
  resources:
    requests:
      cpu: "0.5"
      memory: "512Mi"
  securityContext:
    allowPrivilegeEscalation: false
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    capabilities:
      drop: [ALL]
```

Retrieve the instance connection name:

```bash
gcloud sql instances describe INSTANCE_NAME \
  --project=PROJECT_ID \
  --format="value(connectionName)"
# Output: PROJECT_ID:REGION:INSTANCE_NAME
```

## Workload Identity Setup

Same pattern as AlloyDB, but the GSA needs `roles/cloudsql.client` instead of `roles/alloydb.client`:

```bash
# 1. Create the GCP Service Account
gcloud iam service-accounts create app-sa \
  --project=PROJECT_ID \
  --display-name="GKE App Service Account"

# 2. Grant Cloud SQL client role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:app-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# 3. Grant other required roles
for ROLE in roles/secretmanager.secretAccessor roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:app-sa@PROJECT_ID.iam.gserviceaccount.com" \
    --role="${ROLE}"
done

# 4. Create the Kubernetes Service Account
kubectl create serviceaccount app-ksa --namespace=NAMESPACE

# 5. Annotate the KSA with the GCP SA email
kubectl annotate serviceaccount app-ksa \
  --namespace=NAMESPACE \
  iam.gke.io/gcp-service-account=app-sa@PROJECT_ID.iam.gserviceaccount.com

# 6. Bind GCP SA to allow KSA impersonation
gcloud iam service-accounts add-iam-policy-binding \
  app-sa@PROJECT_ID.iam.gserviceaccount.com \
  --project=PROJECT_ID \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/app-ksa]"
```

## Pod Security Context

Use the same nonroot security context as AlloyDB patterns:

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    fsGroup: 65532
  containers:
    - name: app
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: [ALL]
```

## Full Pod Spec Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
    spec:
      serviceAccountName: app-ksa
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      containers:
        - name: app
          image: us-central1-docker.pkg.dev/PROJECT_ID/repo/app:latest
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: "1"
              memory: "1Gi"
          env:
            - name: DATABASE_URL
              value: "postgresql+asyncpg://app_user:$(DB_PASSWORD)@localhost:5432/appdb"
          envFrom:
            - secretRef:
                name: app-secrets
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 30
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
        - name: cloud-sql-proxy
          image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.11.0
          args:
            - "--structured-logs"
            - "--port=5432"
            - "PROJECT_ID:REGION:INSTANCE_NAME"
          resources:
            requests:
              cpu: "0.5"
              memory: "512Mi"
          securityContext:
            allowPrivilegeEscalation: false
            runAsNonRoot: true
            runAsUser: 65532
            runAsGroup: 65532
            capabilities:
              drop: [ALL]
```

## Connection String Formats

**PostgreSQL (via TCP socket on localhost):**

```
postgresql+asyncpg://DB_USER:DB_PASSWORD@localhost:5432/DB_NAME
postgresql://DB_USER:DB_PASSWORD@localhost:5432/DB_NAME
```

**MySQL:**

```
mysql+aiomysql://DB_USER:DB_PASSWORD@localhost:3306/DB_NAME
```

The proxy always listens on `localhost` inside the pod. The proxy handles TLS to Cloud SQL -- the application connects over plain TCP on localhost (no SSL required in the connection string).

## IAM Database Authentication (Optional)

Instead of password-based auth, use IAM to authenticate directly with the Cloud SQL instance. The GSA email becomes the database user.

```bash
# Create IAM database user
gcloud sql users create app-sa@PROJECT_ID.iam \
  --instance=INSTANCE_NAME \
  --project=PROJECT_ID \
  --type=CLOUD_IAM_SERVICE_ACCOUNT
```

Enable IAM auth on the proxy:

```yaml
args:
  - "--structured-logs"
  - "--auto-iam-authn"    # enable IAM authentication
  - "--port=5432"
  - "PROJECT_ID:REGION:INSTANCE_NAME"
```

Connection string uses the SA email (without `.gserviceaccount.com`) as the username and an empty password:

```
postgresql://app-sa@PROJECT_ID.iam@localhost:5432/DB_NAME
```

## Cloud SQL vs AlloyDB Decision

| Criteria | Cloud SQL | AlloyDB |
|---|---|---|
| PostgreSQL compatibility | Full | Full (Postgres 14+) |
| Performance | Standard | 4x read, 2x write vs Cloud SQL |
| High availability | Multi-zone replica | Managed HA, read pools |
| Price | Lower | Higher |
| Vector search | pgvector extension | Built-in `google_ml_integration` |
| AI integrations | pgvector | AlloyDB AI (Vertex AI embed) |
| Best for | General workloads, cost-sensitive | High-throughput, AI/ML workloads |

## Official References

- <https://cloud.google.com/sql/docs/postgres/connect-kubernetes-engine>
- <https://cloud.google.com/sql/docs/postgres/connect-auth-proxy>
- <https://cloud.google.com/sql/docs/postgres/iam-authentication>
- <https://cloud.google.com/kubernetes-engine/docs/tutorials/workload-identity>
