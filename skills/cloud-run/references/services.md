# Cloud Run Services

## Key Concepts

### Services vs Jobs

| Feature | Services | Jobs |
|---------|----------|------|
| Purpose | HTTP request handling | Batch/scheduled tasks |
| Scaling | Auto-scales with traffic | Runs to completion |
| Billing | Per-request CPU time | Per-execution |
| Timeout | Up to 60 minutes | Up to 24 hours |
| Command | `gcloud run deploy` | `gcloud run jobs deploy` |

### CPU Allocation Modes

1. **Request-based (default)**: CPU only allocated during request processing
   - Best for: Cost optimization, sporadic traffic
   - Limitation: No background processing between requests

2. **Always-allocated**: CPU allocated for entire container lifetime
   - Best for: WebSockets, background tasks, streaming
   - Cost: Higher, but enables more use cases

```bash
# Always-allocated CPU
gcloud run deploy SERVICE --cpu-throttling=false

# Request-based (default)
gcloud run deploy SERVICE --cpu-throttling=true
```

## CLI Commands

### Deployment

```bash
# Basic deploy
gcloud run deploy SERVICE \
  --image=IMAGE_URL \
  --region=REGION \
  --platform=managed

# Full deployment with common options
gcloud run deploy SERVICE \
  --image=gcr.io/PROJECT/IMAGE:TAG \
  --region=us-central1 \
  --cpu=2 \
  --memory=2Gi \
  --concurrency=80 \
  --min-instances=1 \
  --max-instances=100 \
  --timeout=300 \
  --set-env-vars="KEY1=VALUE1,KEY2=VALUE2" \
  --service-account=SA@PROJECT.iam.gserviceaccount.com \
  --allow-unauthenticated

# Deploy without traffic (for testing)
gcloud run deploy SERVICE --image=IMAGE_URL --no-traffic --tag=preview
```

### Traffic Management

```bash
# Send all traffic to latest
gcloud run services update-traffic SERVICE --to-latest

# Split traffic between revisions
gcloud run services update-traffic SERVICE \
  --to-revisions=REVISION1=70,REVISION2=30

# Gradual rollout (10% to latest)
gcloud run services update-traffic SERVICE \
  --to-revisions=LATEST=10

# Tag-based routing
gcloud run services update-traffic SERVICE \
  --to-tags=canary=10

# Rollback to specific revision
gcloud run services update-traffic SERVICE \
  --to-revisions=REVISION_NAME=100
```

### Revision Management

```bash
# List revisions
gcloud run revisions list --service=SERVICE

# Describe revision
gcloud run revisions describe REVISION

# Set tags on revisions
gcloud run services update-traffic SERVICE \
  --set-tags=stable=REVISION1,canary=REVISION2

# Delete old revisions
gcloud run revisions delete REVISION
```

### Service Management

```bash
# List services
gcloud run services list

# Describe service
gcloud run services describe SERVICE --region=REGION

# Delete service
gcloud run services delete SERVICE --region=REGION

# Update service
gcloud run services update SERVICE \
  --update-env-vars="KEY=VALUE" \
  --region=REGION
```

## Concurrency Configuration

### Understanding Concurrency

- **Default**: 80 concurrent requests per instance
- **Maximum**: 1000 concurrent requests per instance
- **Minimum**: 1 (single-threaded apps)

### Tuning Guidelines

| Workload Type | Recommended Concurrency |
|---------------|------------------------|
| I/O-bound async | 80-1000 |
| CPU-intensive | 1-10 |
| Memory-intensive | 10-20 |
| Mixed workloads | 20-50 |

```bash
# Set concurrency
gcloud run deploy SERVICE --concurrency=80

# Single-threaded mode
gcloud run deploy SERVICE --concurrency=1
```

### Language-Specific Notes

**Python**: Set `THREADS` environment variable equal to concurrency

```bash
gcloud run deploy SERVICE --set-env-vars="THREADS=80" --concurrency=80
```

**Node.js**: Use async patterns; single-threaded but handles concurrent I/O well

## Resource Configuration

### CPU and Memory

```bash
# CPU options: 1, 2, 4, 6, 8 vCPUs
gcloud run deploy SERVICE --cpu=2

# Memory: 128Mi to 32Gi
gcloud run deploy SERVICE --memory=2Gi

# Combined
gcloud run deploy SERVICE --cpu=2 --memory=4Gi
```

### Memory Formula

```text
Peak Memory = Standing Memory + (Memory per Request × Concurrency)
```

### GPU Support (Preview)

```bash
gcloud run deploy SERVICE \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --cpu=8 \
  --memory=32Gi
```
