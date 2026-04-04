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

---

## Task Parallelism

Cloud Run Jobs support up to **10,000 parallel tasks** per execution.

```bash
gcloud run jobs deploy parallel-job \
  --image=IMAGE_URL \
  --tasks=1000 \
  --parallelism=50 \
  --task-timeout=3600 \
  --region=us-central1
```

### Work Distribution with Environment Variables

Each task receives injected environment variables for partitioning work:

| Variable | Description |
|----------|-------------|
| `CLOUD_RUN_TASK_INDEX` | Zero-based index of this task (0 to tasks-1) |
| `CLOUD_RUN_TASK_COUNT` | Total number of tasks in the execution |

Example usage in Python:

```python
import os

task_index = int(os.environ["CLOUD_RUN_TASK_INDEX"])
task_count = int(os.environ["CLOUD_RUN_TASK_COUNT"])

# Process this task's slice of work
items = all_items[task_index::task_count]
```

### Timeouts and Retries

| Setting | Default | Maximum | Flag |
|---------|---------|---------|------|
| Task timeout | 10 minutes | 168 hours (7 days) | `--task-timeout` |
| Max retries per task | 3 | N | `--max-retries=N` |

```bash
# Long-running job with custom retry policy
gcloud run jobs deploy long-job \
  --image=IMAGE_URL \
  --task-timeout=86400 \
  --max-retries=1 \
  --region=us-central1
```

---

## Scheduled Execution (Cloud Scheduler)

Trigger Cloud Run Jobs on a cron schedule via Cloud Scheduler.

### Setup

```bash
# Create the scheduled job trigger
gcloud scheduler jobs create http my-job-schedule \
  --location=us-central1 \
  --schedule="0 2 * * *" \
  --uri="https://run.googleapis.com/v2/projects/PROJECT/locations/REGION/jobs/JOB:run" \
  --http-method=POST \
  --oauth-service-account-email=scheduler-sa@PROJECT.iam.gserviceaccount.com \
  --message-body='{}'

# Run manually to test
gcloud scheduler jobs run my-job-schedule --location=us-central1
```

### URI Pattern

```
https://run.googleapis.com/v2/projects/PROJECT/locations/REGION/jobs/JOB:run
```

### Required IAM Roles for Scheduler SA

| Role | Purpose |
|------|---------|
| `roles/cloudscheduler.admin` | Manage Cloud Scheduler jobs |
| `roles/run.invoker` | Trigger Cloud Run Job executions |

```bash
# Grant roles to the scheduler service account
gcloud projects add-iam-policy-binding PROJECT \
  --member=serviceAccount:scheduler-sa@PROJECT.iam.gserviceaccount.com \
  --role=roles/run.invoker
```

### Common Cron Schedules

| Schedule | Meaning |
|----------|---------|
| `0 2 * * *` | Daily at 2:00 AM |
| `0 */6 * * *` | Every 6 hours |
| `0 9 * * 1` | Every Monday at 9:00 AM |
| `*/15 * * * *` | Every 15 minutes |

---

## GPU for Jobs

GPU flags work identically for Jobs as for Services. The `gpu-zonal-redundancy-disabled` annotation is required to ensure scheduling.

```bash
# Deploy GPU job
gcloud run jobs deploy gpu-batch-job \
  --image=IMAGE_URL \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --cpu=8 \
  --memory=32Gi \
  --tasks=10 \
  --parallelism=2 \
  --region=us-central1

# Add required annotation for GPU jobs
gcloud run jobs update gpu-batch-job \
  --update-annotations=run.googleapis.com/gpu-zonal-redundancy-disabled=true \
  --region=us-central1
```

**Quota planning:** GPU quota must cover `GPUs × parallelism`. For 2 parallel tasks with 1 GPU each, you need quota for 2 L4 GPUs in the region.

See [GPU reference](gpu.md) for GPU types, driver details, and ML inference patterns.
