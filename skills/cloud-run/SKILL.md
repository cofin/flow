---
name: cloud-run
description: "Auto-activate for Cloud Run service.yaml, gcloud run commands. Google Cloud Run serverless platform: Dockerfile, containerized services, Cloud Run Jobs, cold starts, traffic splitting. Produces Cloud Run service configurations, Dockerfiles, and deployment workflows for containerized serverless apps on GCP. Use when: deploying containers to Cloud Run, writing Dockerfiles for serverless, or tuning scaling/concurrency. Not for GKE (see gke), Cloud Functions, or non-containerized deployments."
---

# Google Cloud Run Skill

## Overview

Cloud Run is a fully managed serverless platform for running containerized applications. It automatically scales from zero to N based on incoming requests and charges only for resources used during request processing.

## Quick Reference

### Deployment Pipeline

1. **Write Dockerfile** — multi-stage build with non-root user
2. **Build image** — `gcloud builds submit --tag gcr.io/PROJECT/IMAGE:TAG`
3. **Deploy service** — `gcloud run deploy SERVICE --image=IMAGE_URL --region=REGION`
4. **Manage traffic** — `gcloud run services update-traffic SERVICE --to-latest`

### Key Service Configuration

| Setting | Flag | Recommendation |
|---|---|---|
| CPU | `--cpu=N` | 1-8 vCPUs; start with 1 |
| Memory | `--memory=NGi` | 256Mi-32Gi; match to workload |
| Concurrency | `--concurrency=N` | 80 default; lower for memory-heavy handlers |
| Min instances | `--min-instances=N` | 1+ for production to avoid cold starts |
| Max instances | `--max-instances=N` | Set a ceiling to control costs |
| Timeout | `--timeout=N` | Up to 3600s for services, 86400s for jobs |
| CPU allocation | `--cpu-throttling=false` | Use for WebSockets, background tasks |

### Services vs Jobs

| Feature | Services | Jobs |
|---------|----------|------|
| Purpose | HTTP request handling | Batch/scheduled tasks |
| Scaling | Auto-scales with traffic | Runs to completion |
| Timeout | Up to 60 minutes | Up to 24 hours |
| Command | `gcloud run deploy` | `gcloud run jobs deploy` |

### GPU (NVIDIA L4)

```bash
gcloud run deploy SERVICE \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --cpu=8 \
  --memory=32Gi \
  --concurrency=4
```

Minimum: 4 CPU, 16 GiB. Recommended: 8 CPU, 32 GiB. Set `--concurrency` explicitly — no GPU-based autoscaling. See [references/gpu.md](references/gpu.md) for RTX PRO 6000 Blackwell, driver details, and ML inference patterns.

### Production Networking & Secrets

**Direct VPC Egress** — route to AlloyDB/Cloud SQL private IPs without VPC connector overhead:

```bash
gcloud run deploy SERVICE \
  --vpc-egress=private-ranges-only \
  --network=NETWORK \
  --subnet=SUBNET
```

**Secret mounting:**

```bash
--set-secrets=KEY=SECRET_NAME:latest
```

**Env var separator trick** — use `^||^` when values contain commas (e.g., JSON arrays in CORS origins):

```bash
--set-env-vars=^||^CORS_ORIGINS=["https://app.example.com","https://api.example.com"]||OTHER_KEY=value
```

**CORS origin reconciliation workflow:**

1. Auto-discover Cloud Run service URL (`gcloud run services describe`)
2. Discover GKE LB IP and Cloud Shell preview URLs
3. Merge with existing allowed origins, deduplicate
4. Update the secret: `gcloud secrets versions add SECRET_NAME --data-file=-`

**IAP setup summary:**

1. Create OAuth brand: `gcloud iap oauth-brands create --application_title=APP --support_email=EMAIL`
2. Grant IAP service identity: `gcloud projects add-iam-policy-binding PROJECT --member=serviceAccount:service-PROJECT@gcp-sa-iap.iam.gserviceaccount.com --role=roles/run.invoker`
3. Grant authorized users: `--member=user:EMAIL --role=roles/iap.httpsResourceAccessor`
4. Add deployer to prevent lockout: grant deployer `roles/iap.httpsResourceAccessor` before enabling IAP

See [references/iap.md](references/iap.md) for full IAP configuration.

<workflow>

## Workflow

### Step 1: Write the Dockerfile

Use multi-stage builds (base, builder, runner). Install dependencies in the builder stage, copy only the runtime artifacts to the runner stage. Run as a non-root user. Use `tini` as PID 1 for proper signal handling.

### Step 2: Build and Push the Image

Use Cloud Build (`gcloud builds submit`) or a CI pipeline to build and push to Artifact Registry or Container Registry. Tag images with the git SHA for traceability.

### Step 3: Deploy the Service

Deploy with `gcloud run deploy`, setting CPU, memory, concurrency, and min/max instances. Use `--no-traffic` for initial test deployments, then shift traffic with `--to-latest` or percentage-based splits.

### Step 4: Configure Auth and Networking

Use `--allow-unauthenticated` for public APIs. For internal services, use IAM-based auth. Set up IAP (Identity-Aware Proxy) for user-facing apps that need Google login. Use VPC Connector for access to private resources.

### Step 5: Tune for Cold Starts

Set `--min-instances=1` in production. Enable `--cpu-boost` for faster startup. Lazy-load heavy dependencies in application code. Pre-compile bytecode for Python.

</workflow>

<guardrails>

## Guardrails

- **Always set memory and CPU limits** — without explicit limits, Cloud Run uses defaults that may not match your workload and can cause OOM kills
- **Handle cold starts explicitly** — set `--min-instances=1` for latency-sensitive production services; use `--cpu-boost` for faster startup
- **Use IAP for auth (not custom middleware)** — Cloud Run's built-in IAP integration eliminates custom auth code; see [references/iap.md](references/iap.md)
- **Never store state in the container** — Cloud Run instances are ephemeral; use Cloud Storage, Firestore, or a database for persistent state
- **Set `--max-instances`** to prevent runaway scaling and unexpected billing spikes
- **Use `--concurrency`** to match your application's per-instance capacity — too high causes memory pressure, too low wastes resources
- **Always use a non-root user** in Dockerfiles — Cloud Run supports it and it reduces the blast radius of container escapes
- **Always use Direct VPC egress (not VPC connector) for private DB access** — `--vpc-egress=private-ranges-only` gives direct routing to AlloyDB/Cloud SQL private IPs with lower latency and no connector overhead
- **Set `--concurrency` explicitly for GPU workloads** — Cloud Run cannot auto-scale on GPU utilization; the default of 80 will OOM a GPU instance
- **Download models from GCS, not the container image, for models >10 GB** — keeps image build fast and model updates independent of deployments
- **Use startup probes for slow-starting containers** (GPU model loading) — hold traffic until the model is ready; see [references/volumes.md](references/volumes.md)

</guardrails>

<validation>

### Validation Checkpoint

Before delivering configurations, verify:

- [ ] Dockerfile uses multi-stage build with non-root user
- [ ] `--memory` and `--cpu` are explicitly set in the deploy command
- [ ] `--min-instances` is set for production services
- [ ] `--max-instances` is set to prevent unbounded scaling
- [ ] Authentication strategy is defined (IAM, IAP, or `--allow-unauthenticated`)
- [ ] Service account is specified (not using the default compute SA)

</validation>

<example>

## Example

Minimal Dockerfile and deploy command for a Python web service:

```dockerfile
# Dockerfile
FROM python:3.13-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

FROM python:3.13-slim-bookworm AS runner
RUN apt-get update && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home appuser
USER appuser
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["tini", "--"]
CMD ["uvicorn", "myapp.main:app", "--host", "0.0.0.0", "--port", "8080"]
EXPOSE 8080
```

Deploy command:

```bash
# Build and push
gcloud builds submit --tag gcr.io/my-project/myapp:latest

# Deploy with production settings
gcloud run deploy myapp \
    --image=gcr.io/my-project/myapp:latest \
    --region=us-central1 \
    --cpu=1 \
    --memory=512Mi \
    --concurrency=80 \
    --min-instances=1 \
    --max-instances=10 \
    --cpu-boost \
    --service-account=myapp-sa@my-project.iam.gserviceaccount.com \
    --allow-unauthenticated
```

</example>

---

> **Note:** No Gemini CLI extension exists for Cloud Run — this skill provides unique value for Cloud Run deployments, GPU workloads, and production networking patterns not covered by other tooling.

## References Index

For detailed guides and configuration examples, refer to the following documents in `references/`:

- **[Services](references/services.md)**
  - Service deployment, CLI commands, traffic management, concurrency, scaling, and resource configuration.
- **[Jobs](references/jobs.md)**
  - Cloud Run Jobs configuration, execution, and task parallelism.
- **[Performance](references/performance.md)**
  - Cold start optimization, resource tuning, concurrency guidelines, and cost/performance best practices.
- **[Terraform Configuration](references/terraform.md)**
  - IaC examples for services, IAM, and custom domain mappings.
- **[Networking](references/networking.md)**
  - Multi-container sidecars, Ingress settings, VPC Connector, and Secrets Management.
- **[Troubleshooting](references/troubleshooting.md)**
  - Debugging startup failures, latency, memory issues, and security/reliability best practices.
- **[Dockerfile Patterns](references/dockerfile.md)**
  - Multi-stage builds, uv package manager, distroless variants, non-root user setup, and tini init system.
- **[Cloud Build](references/cloudbuild.md)**
  - Cloud Build pipelines, cache warming, multi-target builds, tag strategy, and Artifact Registry push patterns.
- **[Identity-Aware Proxy (IAP)](references/iap.md)**
  - IAP setup for Cloud Run, JWT validation, user auto-provisioning, environment variables, gcloud commands, and Terraform configuration.
- **[GPU Support](references/gpu.md)**
  - NVIDIA L4 and RTX PRO 6000 Blackwell configuration, ML inference best practices, concurrency tuning, and GPU Jobs.
- **[Volumes and Health Checks](references/volumes.md)**
  - Cloud Storage FUSE mounts, NFS (Filestore), startup probes, and liveness probes.

---

## Official References

- <https://docs.cloud.google.com/run/docs>
- <https://docs.cloud.google.com/run/docs/release-notes>
- <https://docs.cloud.google.com/run/docs/configuring/task-timeout>
- <https://docs.cloud.google.com/run/docs/configuring/services/cpu>
- <https://docs.cloud.google.com/run/docs/configuring/services/gpu>
- <https://docs.cloud.google.com/run/docs/mapping-custom-domains>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [GCP Scripting](https://github.com/cofin/flow/blob/main/templates/styleguides/cloud/gcp_scripting.md)
- [Bash](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/bash.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
