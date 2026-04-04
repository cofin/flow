# Cloud Run Volumes and Health Checks

## Cloud Storage FUSE

Mount a GCS bucket as a filesystem volume in your Cloud Run service or job. Requires the **2nd-generation execution environment**.

### Mount Command

```bash
gcloud run deploy SERVICE \
  --add-volume=name=my-data,type=cloud-storage,bucket=MY_BUCKET \
  --add-volume-mount=volume=my-data,mount-path=/data \
  --execution-environment=gen2 \
  --region=us-central1
```

### Volume Options

| Option | Description |
|--------|-------------|
| `readonly` | Mount as read-only (recommended for model loading) |
| `stat-cache-max-size-mb=N` | Override stat cache size (default: 32 MB) |
| `only-dir=subpath` | Mount a subdirectory of the bucket instead of root |
| `uid=N` / `gid=N` | Set file ownership for non-root containers |
| `implicit-dirs` | Enable listing of directories not explicitly created |
| `log-severity=LEVEL` | FUSE log verbosity (e.g., `WARNING`, `ERROR`) |

### Example with Options

```bash
gcloud run deploy SERVICE \
  --add-volume=name=models,type=cloud-storage,bucket=MY_MODELS_BUCKET,readonly=true,implicit-dirs=true \
  --add-volume-mount=volume=models,mount-path=/models \
  --execution-environment=gen2
```

### Caching Overhead

Cloud Storage FUSE adds per-instance memory overhead:

- Stat cache: ~32 MB (configurable via `stat-cache-max-size-mb`)
- Type cache: ~4 MB
- Total: ~36 MB baseline per instance

### Limitations

- **No file locking** — concurrent writes from multiple instances use last-write-wins semantics
- Not suitable for databases or lock-requiring workloads
- Eventual consistency on highly concurrent writes

### Best Use Cases

- Read-heavy workloads (ML model loading, static assets)
- Data processing where each task reads distinct files
- Sharing large artifacts across instances without baking into the image

---

## NFS (Filestore)

Mount a Filestore NFS share for workloads requiring POSIX-compatible shared storage.

### Requirements

- **VPC connectivity required** — Cloud Run service must have VPC access configured
- Use Direct VPC egress (`--vpc-egress=private-ranges-only`) for best performance

### Mount Command

```bash
gcloud run deploy SERVICE \
  --add-volume=name=shared,type=nfs,location=FILESTORE_IP,path=/share_name \
  --add-volume-mount=volume=shared,mount-path=/mnt/shared \
  --execution-environment=gen2 \
  --network=NETWORK \
  --subnet=SUBNET \
  --vpc-egress=private-ranges-only
```

### NFS Configuration Notes

- Mount timeout: 30 seconds
- Uses `no-lock` mode — advisory locks are not supported
- For multiple NFS volumes, mounts are attempted in parallel to reduce startup time

---

## Health Checks

Health checks detect container startup completion, deadlocks, and resource exhaustion.

### Startup Probes

Startup probes delay traffic until the container signals readiness. Critical for GPU workloads loading large models.

```yaml
# service.yaml — HTTP startup probe
apiVersion: serving.knative.dev/v1
kind: Service
spec:
  template:
    spec:
      containers:
        - name: app
          startupProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 0
            periodSeconds: 5
            failureThreshold: 60   # 5s × 60 = 5 min max wait
            timeoutSeconds: 3
```

```yaml
# TCP startup probe (for non-HTTP services)
startupProbe:
  tcpSocket:
    port: 8080
  initialDelaySeconds: 0
  periodSeconds: 5
  failureThreshold: 48
```

```yaml
# gRPC startup probe
startupProbe:
  grpc:
    port: 50051
  periodSeconds: 5
  failureThreshold: 60
```

**Parameter ranges:**

| Parameter | Range | Notes |
|-----------|-------|-------|
| `initialDelaySeconds` | 0–240 | Seconds to wait before first probe |
| `periodSeconds` | 1–240 | Interval between probes |
| `failureThreshold` | 1–N | Failures before container restart |
| `timeoutSeconds` | 1–240 | Per-probe timeout |

**GPU startup pattern** — set `failureThreshold` high to accommodate model loading:

```bash
# Total startup budget = periodSeconds × failureThreshold
# For a 4-min model load: periodSeconds=5, failureThreshold=60 → 5 min budget
```

### Liveness Probes

Liveness probes restart containers that have become deadlocked or exhausted.

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 0
  periodSeconds: 10          # default: 10s
  failureThreshold: 3
  timeoutSeconds: 4
```

```yaml
# gRPC liveness probe
livenessProbe:
  grpc:
    port: 50051
  periodSeconds: 10
  failureThreshold: 3
```

**When to use liveness probes:**

- GPU/CPU-intensive inference services that can deadlock under OOM conditions
- Services with connection pools that can become exhausted
- Long-lived background threads that may silently fail

**Note:** Liveness probes are not supported for startup — use startup probes for initial readiness.

### Applying via gcloud

```bash
gcloud run deploy SERVICE \
  --region=us-central1 \
  --startup-cpu-boost \
  --startup-probe-initial-delay=0 \
  --startup-probe-period=5 \
  --startup-probe-failure-threshold=60 \
  --startup-probe-path=/healthz \
  --liveness-probe-period=10 \
  --liveness-probe-failure-threshold=3 \
  --liveness-probe-path=/healthz
```

## References

- <https://cloud.google.com/run/docs/configuring/healthchecks>
- <https://cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts>
- <https://cloud.google.com/run/docs/configuring/services/nfs-volume-mounts>
