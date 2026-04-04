# AlloyDB on GKE

Production patterns for connecting GKE workloads to AlloyDB using the Auth Proxy sidecar and Workload Identity.

## Architecture

The AlloyDB Auth Proxy runs as a **sidecar container** in the same Pod as the application. The proxy handles authentication (via Workload Identity) and encryption, and exposes AlloyDB on `localhost:5432`. The application connects as if to a local Postgres instance.

```
Pod
├── app-container  →  localhost:5432  →  alloydb-auth-proxy  →  AlloyDB (private IP)
└── alloydb-auth-proxy (sidecar)
```

## Auth Proxy Sidecar Container Spec

```yaml
- name: alloydb-auth-proxy
  image: gcr.io/alloydb-connectors/alloydb-auth-proxy:latest
  args:
    - "projects/PROJECT_ID/locations/REGION/clusters/ALLOYDB_CLUSTER/instances/ALLOYDB_INSTANCE"
    - "--port=5432"
    - "--auto-iam-authn"       # optional: use IAM-based authentication
    - "--structured-logging"   # JSON logs for Cloud Logging
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

The instance URI format is: `projects/PROJECT_ID/locations/REGION/clusters/CLUSTER_NAME/instances/INSTANCE_NAME`

Retrieve it with:

```bash
gcloud alloydb instances describe INSTANCE_NAME \
  --cluster=CLUSTER_NAME \
  --region=REGION \
  --project=PROJECT_ID \
  --format="value(name)"
```

## Workload Identity Setup

Full command sequence to create and configure the GSA, KSA, and binding:

```bash
# 1. Create the GCP Service Account
gcloud iam service-accounts create worker-sa \
  --project=PROJECT_ID \
  --display-name="GKE Worker Service Account"

# 2. Grant required roles to the GSA
ROLES=(
  "roles/alloydb.client"
  "roles/secretmanager.secretAccessor"
  "roles/storage.objectAdmin"
  "roles/logging.logWriter"
  "roles/monitoring.metricWriter"
  "roles/artifactregistry.reader"
)
for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:worker-sa@PROJECT_ID.iam.gserviceaccount.com" \
    --role="${ROLE}"
done

# 3. Create the Kubernetes Service Account
kubectl create serviceaccount worker-ksa --namespace=NAMESPACE

# 4. Annotate the KSA with the GCP SA email
kubectl annotate serviceaccount worker-ksa \
  --namespace=NAMESPACE \
  iam.gke.io/gcp-service-account=worker-sa@PROJECT_ID.iam.gserviceaccount.com

# 5. Allow KSA to impersonate the GCP SA (the binding)
gcloud iam service-accounts add-iam-policy-binding \
  worker-sa@PROJECT_ID.iam.gserviceaccount.com \
  --project=PROJECT_ID \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/worker-ksa]"
```

## Pod Security Context

Always use this security context for AlloyDB proxy pods and application pods:

```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532     # distroless nonroot user
    runAsGroup: 65532
    fsGroup: 65532
  containers:
    - name: app
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: [ALL]
```

The UID 65532 matches the `nonroot` user in distroless images. The AlloyDB Auth Proxy image is distroless; running as root causes it to refuse to start.

## Kubernetes Secrets from Secret Manager

Sync Secret Manager secrets into a Kubernetes secret (KEY=VALUE format):

```bash
# Fetch secret payload and create K8s secret
gcloud secrets versions access latest \
  --secret=MY_SECRET \
  --project=PROJECT_ID \
  > /tmp/app-secrets.env

kubectl delete secret app-secrets -n NAMESPACE --ignore-not-found=true
kubectl create secret generic app-secrets \
  -n NAMESPACE \
  --from-env-file=/tmp/app-secrets.env

rm -f /tmp/app-secrets.env
```

Reference in pod spec:

```yaml
envFrom:
  - secretRef:
      name: app-secrets
```

Or mount individual keys:

```yaml
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: app-secrets
        key: DATABASE_URL
```

## Full Worker Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-worker
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app-worker
  template:
    metadata:
      labels:
        app: app-worker
      annotations:
        cloud.google.com/compute-class: "Scale-Out"   # Autopilot: prefer scale-out
    spec:
      serviceAccountName: worker-ksa
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      containers:
        - name: worker
          image: us-central1-docker.pkg.dev/PROJECT_ID/repo/app:latest
          command: ["app", "server", "run-worker"]
          resources:
            requests:
              cpu: "4"
              memory: "24Gi"
              ephemeral-storage: "50Gi"
          envFrom:
            - secretRef:
                name: app-secrets
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
        - name: alloydb-auth-proxy
          image: gcr.io/alloydb-connectors/alloydb-auth-proxy:latest
          args:
            - "projects/PROJECT_ID/locations/REGION/clusters/CLUSTER/instances/INSTANCE"
            - "--port=5432"
            - "--structured-logging"
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
      volumes:
        - name: work
          ephemeral:
            volumeClaimTemplate:
              spec:
                accessModes: ["ReadWriteOnce"]
                storageClassName: standard-rwo
                resources:
                  requests:
                    storage: 50Gi
```

## Web Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-web
spec:
  replicas: 2
  selector:
    matchLabels:
      app: app-web
  template:
    spec:
      serviceAccountName: worker-ksa
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      containers:
        - name: web
          image: us-central1-docker.pkg.dev/PROJECT_ID/repo/app:latest
          command: ["app", "server", "run", "--host", "0.0.0.0", "--port", "8080"]
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: "1"
              memory: "1Gi"
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
        - name: alloydb-auth-proxy
          image: gcr.io/alloydb-connectors/alloydb-auth-proxy:latest
          args:
            - "projects/PROJECT_ID/locations/REGION/clusters/CLUSTER/instances/INSTANCE"
            - "--port=5432"
            - "--structured-logging"
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

## Job Patterns

### Database Initialization Job

Use `google/alloydbomni` image for psql access when the AlloyDB Auth Proxy sidecar is not needed (direct private IP access during setup):

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-init
spec:
  ttlSecondsAfterFinished: 300    # auto-delete after 5 minutes
  backoffLimit: 0                  # no retries (CREATE DATABASE is not idempotent)
  template:
    spec:
      serviceAccountName: worker-ksa
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      restartPolicy: Never
      containers:
        - name: create-db
          image: google/alloydbomni:latest
          command:
            - bash
            - -euc
            - |
              PG="host=${PGHOST} dbname=postgres user=postgres sslmode=require"
              if psql "$PG" -tc "SELECT 1 FROM pg_database WHERE datname = 'mydb'" | grep -q 1; then
                echo "Database already exists"
              else
                psql "$PG" -c "CREATE DATABASE mydb"
                echo "Database created"
              fi
          env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-init-creds
                  key: PGPASSWORD
            - name: PGHOST
              valueFrom:
                secretKeyRef:
                  name: db-init-creds
                  key: PGHOST
          resources:
            requests:
              cpu: "0.2"
              memory: "256Mi"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
```

### Migration Job with Auth Proxy as initContainer (sidecar)

In Kubernetes 1.29+, use `restartPolicy: Always` on an initContainer to run it as a sidecar (stays alive while the main container runs):

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
spec:
  ttlSecondsAfterFinished: 600
  backoffLimit: 3
  template:
    spec:
      serviceAccountName: worker-ksa
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
        fsGroup: 65532
      restartPolicy: Never
      initContainers:
        - name: alloydb-auth-proxy
          image: gcr.io/alloydb-connectors/alloydb-auth-proxy:latest
          restartPolicy: Always    # sidecar: stays alive while main containers run
          args:
            - "projects/PROJECT_ID/locations/REGION/clusters/CLUSTER/instances/INSTANCE"
            - "--port=5432"
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
      containers:
        - name: migrate
          image: us-central1-docker.pkg.dev/PROJECT_ID/repo/app:latest
          command: ["app", "manage", "db", "upgrade", "--no-prompt"]
          envFrom:
            - secretRef:
                name: app-secrets
          resources:
            requests:
              cpu: "0.5"
              memory: "512Mi"
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: [ALL]
```

## Queue-Depth HPA

Scale worker deployments based on database queue depth published to Cloud Monitoring.

### Step 1: Install Custom Metrics Stackdriver Adapter

The adapter exposes Cloud Monitoring metrics to the HPA via the `external.metrics.k8s.io` API group.

```bash
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/k8s-stackdriver/master/custom-metrics-stackdriver-adapter/deploy/production/adapter_new_resource_model.yaml
```

On GKE Autopilot, bind the adapter's KSA to a GCP SA with `roles/monitoring.viewer`:

```bash
kubectl annotate serviceaccount custom-metrics-stackdriver-adapter \
  --namespace=custom-metrics \
  --overwrite \
  iam.gke.io/gcp-service-account=worker-sa@PROJECT_ID.iam.gserviceaccount.com

gcloud iam service-accounts add-iam-policy-binding \
  worker-sa@PROJECT_ID.iam.gserviceaccount.com \
  --project=PROJECT_ID \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[custom-metrics/custom-metrics-stackdriver-adapter]"

# Restart to pick up the new WI annotation
kubectl rollout restart deployment/custom-metrics-stackdriver-adapter -n custom-metrics
```

### Step 2: CronJob Queue Monitor

The monitor uses two containers: `alloydbomni` (has psql, lacks curl) as an initContainer to query the DB, and `curlimages/curl` to push the metric to Cloud Monitoring. Communicate via a shared `emptyDir` volume.

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: queue-monitor
spec:
  schedule: "* * * * *"      # every minute
  concurrencyPolicy: Forbid   # skip if previous run is still running
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      ttlSecondsAfterFinished: 120
      activeDeadlineSeconds: 55   # must finish before next minute
      template:
        spec:
          serviceAccountName: worker-ksa
          securityContext:
            runAsNonRoot: true
            runAsUser: 65532
            runAsGroup: 65532
          restartPolicy: Never
          volumes:
            - name: shared
              emptyDir: {}
          initContainers:
            - name: query
              image: google/alloydbomni:latest
              command:
                - bash
                - -euc
                - |
                  COUNT=$(psql "${DATABASE_URL}" \
                    -qtAc "SELECT COUNT(*) FROM job WHERE status IN ('pending','scheduled')" \
                    2>/dev/null || echo 0)
                  echo "${COUNT}" > /shared/count
              envFrom:
                - secretRef:
                    name: app-secrets
              volumeMounts:
                - name: shared
                  mountPath: /shared
              resources:
                requests:
                  cpu: "100m"
                  memory: "128Mi"
              securityContext:
                allowPrivilegeEscalation: false
                capabilities:
                  drop: [ALL]
          containers:
            - name: push
              image: curlimages/curl:latest
              command:
                - sh
                - -euc
                - |
                  COUNT=$(cat /shared/count | tr -d '[:space:]')
                  TOKEN=$(curl -sf --max-time 5 \
                    -H "Metadata-Flavor: Google" \
                    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token" \
                    | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
                  NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
                  curl -sf --max-time 10 -X POST \
                    -H "Authorization: Bearer ${TOKEN}" \
                    -H "Content-Type: application/json" \
                    -d "{\"timeSeries\":[{\"metric\":{\"type\":\"custom.googleapis.com/app/queue_depth\"},\"resource\":{\"type\":\"global\",\"labels\":{\"project_id\":\"PROJECT_ID\"}},\"points\":[{\"interval\":{\"endTime\":\"${NOW}\"},\"value\":{\"int64Value\":\"${COUNT}\"}}]}]}" \
                    "https://monitoring.googleapis.com/v3/projects/PROJECT_ID/timeSeries"
                  echo "Pushed queue depth: ${COUNT}"
              volumeMounts:
                - name: shared
                  mountPath: /shared
              resources:
                requests:
                  cpu: "100m"
                  memory: "64Mi"
              securityContext:
                allowPrivilegeEscalation: false
                capabilities:
                  drop: [ALL]
```

### Step 3: Seed Initial Metric

Without seeding, the HPA shows "unable to get external metric" until the CronJob pushes its first value. Seed immediately after deploying:

```bash
TOKEN=$(gcloud auth print-access-token)
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
curl -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"timeSeries\":[{\"metric\":{\"type\":\"custom.googleapis.com/app/queue_depth\"},\"resource\":{\"type\":\"global\",\"labels\":{\"project_id\":\"PROJECT_ID\"}},\"points\":[{\"interval\":{\"endTime\":\"${NOW}\"},\"value\":{\"int64Value\":\"0\"}}]}]}" \
  "https://monitoring.googleapis.com/v3/projects/PROJECT_ID/timeSeries"
```

### Step 4: HPA Manifest

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app-worker
  minReplicas: 1
  maxReplicas: 10
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300   # wait 5 min before scaling down
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    - type: External
      external:
        metric:
          name: custom.googleapis.com|app|queue_depth   # | not / in HPA
        target:
          type: AverageValue
          averageValue: "15"   # scale up when avg queue depth > 15 per replica
```

**Important:** Verify the external metric is readable before applying the HPA with the external metric section:

```bash
kubectl get --raw "/apis/external.metrics.k8s.io/v1beta1/namespaces/NAMESPACE/custom.googleapis.com|app|queue_depth"
```

If the metric is not yet readable, apply the HPA with CPU/Memory only first, then add the external metric after the CronJob has pushed data.

## Connection String Format

```
postgresql+asyncpg://DB_USER:DB_PASSWORD@localhost:5432/DB_NAME
```

The proxy always listens on `localhost` inside the pod. AlloyDB requires `sslmode=require` for direct connections (bypassing the proxy) but the proxy itself handles TLS -- app connects over plain TCP on localhost.

## Official References

- <https://cloud.google.com/alloydb/docs/auth-proxy/overview>
- <https://cloud.google.com/alloydb/docs/connect-kubernetes>
- <https://cloud.google.com/kubernetes-engine/docs/tutorials/workload-identity>
