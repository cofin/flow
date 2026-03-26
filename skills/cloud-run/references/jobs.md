# Cloud Run Jobs

## Overview

Cloud Run Jobs are designed for batch and scheduled tasks that run to completion, as opposed to Services which handle HTTP requests. Jobs support up to 24-hour timeouts and are billed per-execution.

## CLI Commands

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

## Services vs Jobs Comparison

| Feature | Services | Jobs |
|---------|----------|------|
| Purpose | HTTP request handling | Batch/scheduled tasks |
| Scaling | Auto-scales with traffic | Runs to completion |
| Billing | Per-request CPU time | Per-execution |
| Timeout | Up to 60 minutes | Up to 24 hours |
| Command | `gcloud run deploy` | `gcloud run jobs deploy` |
