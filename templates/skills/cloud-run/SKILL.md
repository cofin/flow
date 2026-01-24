---
name: cloud-run
description: Expert knowledge for Google Cloud Run serverless containers. Use when deploying containerized applications, configuring services/jobs, managing traffic, optimizing cold starts, or troubleshooting Cloud Run deployments.
---

# Google Cloud Run Skill

## Overview

Cloud Run is a fully managed serverless platform for running containerized applications. It automatically scales from zero to N based on incoming requests and charges only for resources used during request processing.

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

## Cold Start Optimization

### Strategies

1. **Minimum Instances**: Keep containers warm
```bash
gcloud run deploy SERVICE --min-instances=1
```

2. **Startup CPU Boost**: Temporarily increase CPU during startup
```bash
gcloud run deploy SERVICE --cpu-boost
```

3. **Application Optimization**:
   - Use minimal base images (Alpine, Distroless)
   - Lazy-load heavy dependencies
   - Defer non-critical initialization
   - Move heavy operations to background threads

4. **Image Optimization**:
   - Image size doesn't affect cold start directly
   - Focus on reducing initialization complexity
   - Pre-compile bytecode (Python: `--compile-bytecode`)

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

```
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

### Jobs

```bash
# Deploy job
gcloud run jobs deploy JOB \
  --image=IMAGE_URL \
  --region=REGION \
  --tasks=10 \
  --parallelism=5 \
  --task-timeout=3600

# Execute job
gcloud run jobs execute JOB --region=REGION

# List job executions
gcloud run jobs executions list --job=JOB
```

## Terraform Configuration

### Basic Service

```hcl
resource "google_cloud_run_v2_service" "default" {
  name     = "my-service"
  location = "us-central1"

  template {
    containers {
      image = "gcr.io/my-project/my-image:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      env {
        name  = "ENV"
        value = "production"
      }

      # Secret from Secret Manager
      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/healthz"
        }
        initial_delay_seconds = 0
        timeout_seconds       = 1
        period_seconds        = 3
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/healthz"
        }
        period_seconds = 30
      }
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 100
    }

    max_instance_request_concurrency = 80
    timeout                          = "300s"
    service_account                  = google_service_account.run_sa.email
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}
```

### IAM Configuration

```hcl
# Public access
resource "google_cloud_run_service_iam_member" "public" {
  service  = google_cloud_run_v2_service.default.name
  location = google_cloud_run_v2_service.default.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Authenticated only
resource "google_cloud_run_service_iam_member" "auth" {
  service  = google_cloud_run_v2_service.default.name
  location = google_cloud_run_v2_service.default.location
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.invoker_sa}"
}
```

### Custom Domain

```hcl
resource "google_cloud_run_domain_mapping" "default" {
  location = "us-central1"
  name     = "api.example.com"

  metadata {
    namespace = var.project_id
  }

  spec {
    route_name = google_cloud_run_v2_service.default.name
  }
}
```

## Multi-Container Services

Cloud Run supports sidecar containers for proxies, logging, etc.

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: multi-container-service
  annotations:
    run.googleapis.com/launch-stage: BETA
spec:
  template:
    metadata:
      annotations:
        # Container startup ordering
        run.googleapis.com/container-dependencies: "{nginx: [app]}"
    spec:
      containers:
        # Ingress container (receives traffic)
        - name: nginx
          image: nginx
          ports:
            - containerPort: 8080
          resources:
            limits:
              cpu: 500m
              memory: 256Mi
          startupProbe:
            tcpSocket:
              port: 8080
            timeoutSeconds: 240

        # Sidecar container
        - name: app
          image: my-app:latest
          env:
            - name: PORT
              value: "8888"
          resources:
            limits:
              cpu: 1000m
              memory: 512Mi
```

## Ingress Configuration

```bash
# Internal only (VPC)
gcloud run deploy SERVICE --ingress=internal

# Internal + Cloud Load Balancing
gcloud run deploy SERVICE --ingress=internal-and-cloud-load-balancing

# All traffic (public)
gcloud run deploy SERVICE --ingress=all
```

## VPC Connector

```bash
# Create connector
gcloud compute networks vpc-access connectors create CONNECTOR \
  --region=REGION \
  --network=VPC_NETWORK \
  --range=10.8.0.0/28

# Deploy with connector
gcloud run deploy SERVICE \
  --vpc-connector=CONNECTOR \
  --vpc-egress=all-traffic
```

## Secrets Management

```bash
# Use Secret Manager secret as env var
gcloud run deploy SERVICE \
  --set-secrets="DB_PASSWORD=db-password:latest"

# Mount secret as file
gcloud run deploy SERVICE \
  --set-secrets="/secrets/config.json=app-config:latest"
```

## Best Practices

### Cost Optimization

1. **Use appropriate concurrency** - Higher concurrency = fewer instances = lower cost
2. **Set min-instances wisely** - Balance cold starts vs always-on cost
3. **Use request-based CPU** unless you need background processing
4. **Right-size CPU/memory** - Don't over-provision

### Performance

1. **Enable startup CPU boost** for faster cold starts
2. **Use health probes** to ensure readiness before receiving traffic
3. **Optimize container startup** - lazy load, async init
4. **Use regional deployments** close to users

### Security

1. **Use Workload Identity** instead of service account keys
2. **Store secrets in Secret Manager**
3. **Set appropriate ingress controls**
4. **Use VPC Connector for internal resources**
5. **Enable binary authorization** for trusted images only

### Reliability

1. **Set appropriate timeouts** for your workload
2. **Configure retries** for transient failures
3. **Use traffic splitting** for safe deployments
4. **Monitor with Cloud Monitoring** and set alerts

## Troubleshooting

### Container Fails to Start

```bash
# Check logs
gcloud run services logs read SERVICE --region=REGION

# Check revision status
gcloud run revisions describe REVISION --region=REGION
```

### High Latency

1. Check cold start frequency (enable min-instances)
2. Review concurrency settings
3. Check for CPU throttling
4. Profile application startup

### Memory Issues

1. Increase memory limit
2. Check for memory leaks
3. Reduce concurrency
4. Review in-memory caching

## Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [General Development Tips](https://cloud.google.com/run/docs/tips/general)
- [Cloud Run Samples](https://github.com/GoogleCloudPlatform/cloud-run-samples)
