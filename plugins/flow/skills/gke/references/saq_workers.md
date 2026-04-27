# SAQ Worker Deployment on GKE

Patterns for deploying SAQ (Simple Async Queue) workers as Kubernetes deployments alongside Litestar web applications.

## Architecture Overview

SAQ workers process background tasks from Redis-backed queues. Each worker deployment handles one or more named queues with configurable concurrency. The Litestar web application enqueues tasks; workers consume them.

```text
┌──────────────┐     enqueue     ┌───────┐     dequeue     ┌─────────────────┐
│  Litestar    │ ──────────────> │ Redis │ <────────────── │  SAQ Workers    │
│  Web App     │                 │       │                 │  (K8s Deploys)  │
└──────────────┘                 └───────┘                 └─────────────────┘
```

## Queue Distribution Strategy

Distribute queues across worker deployments based on workload characteristics:

| Queue | Purpose | Concurrency | Replicas | Notes |
|-------|---------|-------------|----------|-------|
| `default` | General background tasks | 4 | 2+ | Catch-all queue |
| `push` | Push notifications, webhooks | 4 | 2+ | I/O bound, higher concurrency OK |
| `ingress` | Data ingestion/processing | 2 | 2+ | May be CPU-heavy |
| `mailers` | Email sending | 4 | 1-2 | Rate-limited by SMTP provider |
| `pull` | External data fetching | 2 | 1-2 | Network-bound |
| `scheduler` | Periodic/cron tasks | 1 | **1 only** | Must be single replica |

## Worker Deployment Configuration

### General Workers (Multi-Queue)

Group related queues into a single deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-worker-default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: myapp
      component: worker-default
  template:
    metadata:
      labels:
        app: myapp
        component: worker-default
    spec:
      serviceAccountName: myapp-sa
      securityContext:
        runAsNonRoot: true
        runAsUser: 65532
        runAsGroup: 65532
      containers:
        - name: worker
          image: us-central1-docker.pkg.dev/PROJECT/repo/app:latest
          command:
            - "app"
            - "server"
            - "run-worker"
            - "--queues"
            - "default,push,ingress"
            - "--concurrency"
            - "4"
          resources:
            requests:
              cpu: 250m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 1Gi
          envFrom:
            - secretRef:
                name: myapp-secrets
      terminationGracePeriodSeconds: 60
```

### Scheduler Worker (Single Replica)

The scheduler queue runs periodic/cron tasks and must be constrained to a single replica to prevent duplicate execution:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-worker-scheduler
spec:
  replicas: 1                    # CRITICAL: Never scale beyond 1
  strategy:
    type: Recreate               # Avoid overlapping pods during rollout
  selector:
    matchLabels:
      app: myapp
      component: worker-scheduler
  template:
    metadata:
      labels:
        app: myapp
        component: worker-scheduler
    spec:
      containers:
        - name: worker
          image: us-central1-docker.pkg.dev/PROJECT/repo/app:latest
          command:
            - "app"
            - "server"
            - "run-worker"
            - "--queues"
            - "scheduler"
            - "--concurrency"
            - "1"
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
      terminationGracePeriodSeconds: 60
```

## Worker Concurrency Configuration

Concurrency controls how many tasks a single worker process handles simultaneously:

- **CPU-bound tasks** (data processing, parsing): concurrency 1-2
- **I/O-bound tasks** (API calls, email, notifications): concurrency 4-8
- **Scheduler**: always concurrency 1

Set via the `--concurrency` CLI flag or environment variable:

```bash
app server run-worker --queues default,push --concurrency 4
```

## Graceful Shutdown

Workers need time to finish in-progress tasks before termination:

```yaml
spec:
  terminationGracePeriodSeconds: 60   # Match or exceed max task duration
```

SAQ workers handle `SIGTERM` by:

1. Stopping acceptance of new tasks
2. Waiting for in-progress tasks to complete
3. Exiting cleanly

Set `terminationGracePeriodSeconds` to at least the maximum expected task duration. If tasks can run longer, implement checkpointing or use heartbeat-based stale detection to requeue interrupted tasks.

## Stale Task Recovery

Configure heartbeat and stale detection to handle worker crashes:

| Setting | Default | Purpose |
|---------|---------|---------|
| `HEARTBEAT_INTERVAL` | 30s | How often running tasks send heartbeats |
| `STALE_AFTER_MINUTES` | 1.5min | Time without heartbeat before task is considered stale |
| `MAX_CONCURRENT_JOBS` | 4 | Maximum concurrent tasks per worker |

The stale threshold must be at least 3x the heartbeat interval to avoid false positives.

## In-Process vs Separate Workers

SAQ workers can run in two modes:

- **In-process** (`INPROCESS_WORKER=true`): Worker runs inside the Litestar web process. Suitable for development and small deployments.
- **Separate process** (`INPROCESS_WORKER=false`): Worker runs as a dedicated Kubernetes deployment. Required for production to isolate background task failures from web serving.

## Official References

- <https://github.com/tobymao/saq>
- <https://saq-py.readthedocs.io/>
- <https://kubernetes.io/docs/concepts/workloads/controllers/deployment/>
- <https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination>
