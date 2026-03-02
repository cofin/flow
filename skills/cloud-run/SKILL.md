---
name: cloud-run
description: Expert knowledge for Google Cloud Run serverless containers. Use when deploying containerized applications, configuring services/jobs, managing traffic, optimizing cold starts, or troubleshooting Cloud Run deployments.
---

# Google Cloud Run Skill

## Overview

Cloud Run is a fully managed serverless platform for containerized workloads.
It supports:
- **Services** for HTTP/gRPC request-driven workloads
- **Jobs** for batch workloads that run to completion

Cloud Run can scale to zero and supports both request-based and instance-based billing, depending on configuration.

## Key Concepts

### Services vs Jobs

| Feature | Services | Jobs |
|---------|----------|------|
| Purpose | HTTP/gRPC request handling | Batch/scheduled tasks |
| Scaling | Auto-scales with traffic | Runs tasks to completion |
| Billing | Request-based (default) or instance-based | Instance-based |
| Timeout | Up to 60 minutes per request | Up to 168 hours (7 days) per task |
| Command | `gcloud run deploy` | `gcloud run jobs deploy` |

### Billing/CPU Allocation Modes (Services)

1. **Request-based billing (default)**: CPU is allocated during request handling/startup/shutdown
   - Best for: Cost optimization, intermittent traffic
   - Limitation: No sustained CPU between requests

2. **Instance-based billing**: CPU is allocated for the full instance lifecycle
   - Best for: Background processing, long-lived connections, streaming
   - Tradeoff: Higher baseline cost

```bash
# Instance-based billing / always allocated CPU
gcloud run deploy SERVICE --no-cpu-throttling

# Request-based billing / throttled CPU (default)
gcloud run deploy SERVICE --cpu-throttling
```

## Cold Start Optimization

### Strategies

1. **Minimum instances**: keep containers warm
```bash
gcloud run deploy SERVICE --min-instances=1
```

2. **Startup CPU boost**: temporarily increase CPU during startup
```bash
gcloud run deploy SERVICE --cpu-boost
```

3. **Application optimization**:
   - Keep startup paths lean
   - Lazy-load heavy dependencies
   - Defer non-critical initialization
   - Avoid expensive global initialization

4. **Image optimization**:
   - Prefer minimal/base hardened images (for security and transfer efficiency)
   - Focus primarily on startup behavior (cold start is usually init-bound)

## Concurrency Configuration

### Understanding Concurrency

- **Default**: 80 concurrent requests per instance
- **Maximum**: 1000
- **Minimum**: 1

### Tuning Guidelines

| Workload Type | Recommended Concurrency |
|---------------|------------------------|
| I/O-bound async | 80-1000 |
| CPU-intensive | 1-10 |
| Memory-intensive | 10-50 |
| Mixed workloads | 20-200 |

```bash
# Set concurrency
gcloud run deploy SERVICE --concurrency=80

# Single-request mode
gcloud run deploy SERVICE --concurrency=1
```

### Language-Specific Notes

**Python**: If using threaded servers, align thread count with concurrency target.
```bash
gcloud run deploy SERVICE --set-env-vars="THREADS=80" --concurrency=80
```

**Node.js**: Use async I/O; concurrency applies at the request level per instance.

## Resource Configuration

### CPU and Memory

```bash
# CPU supports fractional and whole values (example values shown)
gcloud run deploy SERVICE --cpu=1

# Memory supports up to 32Gi (min/max depend on chosen CPU)
gcloud run deploy SERVICE --memory=2Gi

# Combined
gcloud run deploy SERVICE --cpu=2 --memory=4Gi
```

### CPU-Memory Coupling (Common Values)

| CPU | Memory range |
|-----|--------------|
| `0.08` | up to `512Mi` |
| `0.5` | up to `1Gi` |
| `1` | up to `4Gi` |
| `2` | up to `8Gi` |
| `4` | `2Gi` to `16Gi` |
| `6` | `4Gi` to `24Gi` |
| `8` | `4Gi` to `32Gi` |

### Memory Formula

```
Peak Memory = Standing Memory + (Memory per Request × Concurrency)
```

### GPU Support

```bash
gcloud run deploy SERVICE \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --cpu=8 \
  --memory=32Gi
```

Notes:
- Cloud Run GPU supports NVIDIA L4.
- Services GPU and Jobs GPU are available; verify latest region support before deploy.
- GPU workloads require higher minimum CPU/memory (at least 4 CPU and 16Gi memory).

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
  --image=us-docker.pkg.dev/PROJECT/REPO/IMAGE:TAG \
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

# Rollback to a specific revision
gcloud run services update-traffic SERVICE \
  --to-revisions=REVISION_NAME=100

# Tag-based routing
gcloud run services update-traffic SERVICE \
  --set-tags=stable=REVISION1,canary=REVISION2
```

### Revision Management

```bash
# List revisions
gcloud run revisions list --service=SERVICE

# Describe revision
gcloud run revisions describe REVISION

# Delete revision
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

# Update service env vars
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
  --task-timeout=1h \
  --max-retries=3

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
      image = "us-docker.pkg.dev/my-project/my-repo/my-image:latest"

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
        period_seconds    = 3
        failure_threshold = 3
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
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.default.name
  location = google_cloud_run_v2_service.default.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Authenticated service account access
resource "google_cloud_run_v2_service_iam_member" "auth" {
  name     = google_cloud_run_v2_service.default.name
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

Notes:
- Domain mappings have regional and certificate capability limits.
- For advanced TLS controls and broader coverage, use Cloud Load Balancing.

## Multi-Container Services

Cloud Run supports sidecars (for example: proxies, collectors, adapters).

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: multi-container-service
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

Notes:
- Exactly one container is ingress-facing.
- Explicitly configure the ingress container port.

## Ingress Configuration

```bash
# Internal only
gcloud run deploy SERVICE --ingress=internal

# Internal + External Application Load Balancer
gcloud run deploy SERVICE --ingress=internal-and-cloud-load-balancing

# Public
gcloud run deploy SERVICE --ingress=all
```

## VPC Egress

Prefer **Direct VPC egress** for new deployments.
Use Serverless VPC Access connectors when Direct VPC egress is not suitable.

### Direct VPC egress (recommended)

```bash
gcloud run deploy SERVICE \
  --network=VPC_NETWORK \
  --subnet=SUBNET
```

### Serverless VPC Access connector

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
# Secret Manager secret as env var
gcloud run deploy SERVICE \
  --set-secrets="DB_PASSWORD=db-password:latest"

# Secret Manager secret mounted as file
gcloud run deploy SERVICE \
  --set-secrets="/secrets/config.json=app-config:latest"
```

## Best Practices

### Cost Optimization

1. Set concurrency intentionally (higher concurrency can lower cost for I/O-heavy apps)
2. Use min instances only where latency SLOs require it
3. Default to request-based billing unless you need background CPU
4. Right-size CPU/memory; revisit after production metrics

### Performance

1. Enable startup CPU boost for startup-heavy apps
2. Use startup/liveness probes for reliable readiness behavior
3. Keep init paths short; defer optional startup work
4. Deploy in regions near primary users/dependencies

### Security

1. Use user-managed service accounts (service identity), not static keys
2. Store secrets in Secret Manager
3. Restrict ingress appropriately
4. Use VPC egress controls for private dependencies
5. Use Binary Authorization when supply-chain controls are required

### Reliability

1. Set realistic timeouts for service requests and job tasks
2. Configure retries for transient failures
3. Use traffic splitting/tags for safer rollouts
4. Monitor with Cloud Monitoring and logs-based alerting

## Troubleshooting

### Container Fails to Start

```bash
# Read service logs
gcloud run services logs read SERVICE --region=REGION

# Inspect revision details
gcloud run revisions describe REVISION --region=REGION
```

### High Latency

1. Check cold-start frequency (`min-instances`, startup time)
2. Revisit concurrency tuning
3. Check CPU throttling/billing mode fit
4. Profile startup and slow handlers

### Memory Issues

1. Increase memory limit
2. Detect leaks and unbounded caches
3. Reduce concurrency for memory-heavy requests
4. Validate per-request memory profile under load

## Where to Verify and Learn More (Official)

- Product docs: https://cloud.google.com/run/docs
- Release notes: https://cloud.google.com/run/docs/release-notes
- Quotas and limits: https://cloud.google.com/run/quotas
- CPU allocation/billing mode: https://cloud.google.com/run/docs/configuring/cpu-allocation
- Services CPU tuning: https://cloud.google.com/run/docs/configuring/services/cpu
- Services memory limits: https://cloud.google.com/run/docs/configuring/services/memory-limits
- Concurrency: https://cloud.google.com/run/docs/about-concurrency
- Jobs task timeout: https://cloud.google.com/run/docs/configuring/task-timeout
- Services GPU: https://cloud.google.com/run/docs/configuring/services/gpu
- Jobs GPU: https://cloud.google.com/run/docs/configuring/jobs/gpu
- Multi-container services: https://cloud.google.com/run/docs/deploying#sidecars
- Ingress controls: https://cloud.google.com/run/docs/securing/ingress
- VPC connectivity (Direct egress and connectors): https://cloud.google.com/run/docs/configuring/connecting-vpc
- Secrets: https://cloud.google.com/run/docs/configuring/services/secrets
- Domain mapping: https://cloud.google.com/run/docs/mapping-custom-domains
- Binary Authorization for Cloud Run: https://cloud.google.com/binary-authorization/docs/run/enabling-binauthz-cloud-run

## Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [General Development Tips](https://cloud.google.com/run/docs/tips/general)
- [Cloud Run Samples](https://github.com/GoogleCloudPlatform/cloud-run-samples)

## Official References

- https://cloud.google.com/run/docs
- https://cloud.google.com/run/docs/release-notes
- https://cloud.google.com/run/docs/configuring/task-timeout
- https://cloud.google.com/run/docs/configuring/services/cpu
- https://cloud.google.com/run/docs/configuring/services/gpu
- https://cloud.google.com/run/docs/mapping-custom-domains

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [GCP Scripting](https://github.com/cofin/flow/blob/main/templates/styleguides/cloud/gcp_scripting.md)
- [Bash](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/bash.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
