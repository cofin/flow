---
name: gcp
description: "Auto-activate for gcloud commands, .gcloudignore, app.yaml. Google Cloud Platform expert: gcloud CLI, IAM, service accounts, Cloud Storage, Pub/Sub, BigQuery, Vertex AI. Use when: managing GCP resources, scripting gcloud commands, or configuring any GCP service. Not for AWS, Azure, or non-GCP cloud providers."
---

# Google Cloud Platform (GCP) Skill

## Service Overview

Use the dedicated `terraform` skill when the question is primarily about Terraform layout, state boundaries, brownfield import/export, workspaces, or CI-driven plan/apply workflows. Keep this `gcp` skill focused on Google Cloud services and `gcloud`-centric operations.

### Core Services

- **Compute**:
  - **Cloud Run**: Serverless containers (default choice for stateless apps).
  - **GKE**: Managed Kubernetes for complex orchestrations.
  - **Compute Engine**: Raw VMs for specific OS/kernel needs.
- **Data & Storage**:
  - **Cloud Storage (GCS)**: Object storage.
  - **Cloud SQL**: Managed PostgreSQL/MySQL/SQL Server.
  - **BigQuery**: Serverless data warehouse (analytics).
  - **Firestore**: NoSQL document database.
- **AI/ML**:
  - **Vertex AI**: Unified platform for models (Gemini, PaLM), training, and deployment.

<workflow>

## `gcloud` CLI & Scripting

### Configuration & Auth

<guardrails>

Avoid interactive prompts in scripts.

</guardrails>

<example>

```bash
# Production/CI: Use Service Account Key or Workload Identity
gcloud auth activate-service-account --key-file=key.json

# Local Dev: User Login
gcloud auth login
gcloud config set project MY_PROJECT_ID
```

</example>

### Scripting Best Practices

#### 1. Structured Output

Never parse default text output. Use `--format` (json/yaml) and `--filter`.

<example>

```bash
# Bad
gcloud compute instances list | grep RUNNING

# Good (Parseable JSON)
gcloud compute instances list --format="json"

# Good (Filter + Specific Value)
gcloud run services list \
  --filter="status.conditions.status=True AND metadata.name:my-service" \
  --format="value(status.url)"
```

</example>

#### 2. Deterministic Filters

Flatten complex resources to find what you need.

<example>

```bash
# Find latest revision of a service
gcloud run revisions list \
  --service=my-service \
  --sort-by="~metadata.creationTimestamp" \
  --limit=1 \
  --format="value(metadata.name)"
```

</example>

#### 3. Quiet Mode

Suppress "updates available" warnings and prompts.

<example>

```bash
export CLOUDSDK_CORE_DISABLE_PROMPTS=1
gcloud ... --quiet
```

</example>

## Automation Patterns

### 1. Cloud Run Deployment

Standard pattern for deploying containers.

<example>

```bash
gcloud run deploy my-service \
  --image gcr.io/my-project/my-image:tag \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DEBUG=true,DB_HOST=10.0.0.2"
```

</example>

### 2. Secret Management

<guardrails>

Access secrets securely (requires Secret Manager API).

</guardrails>

<example>

```bash
# Mount as volume in Cloud Run (Preferred)
gcloud run deploy ... --set-secrets="/secrets/db=my-db-secret:latest"

# Access via CLI (for ops scripts)
gcloud secrets versions access latest --secret="my-secret"
```

</example>

</workflow>

## AlloyDB

AlloyDB is a fully managed PostgreSQL-compatible database with columnar engine and ML-assisted auto-vacuum.

### Cluster / Instance Model

- **Cluster**: regional resource containing one primary and optional read pool instances.
- **Primary instance**: read-write; choose machine type and vCPUs.
- **Read pool**: horizontally scalable read-only replicas within the same cluster.

```bash
# Create a cluster
gcloud alloydb clusters create my-cluster \
  --region=us-central1 \
  --password=SECRET \
  --network=projects/MY_PROJECT/global/networks/default

# Create primary instance
gcloud alloydb instances create my-primary \
  --cluster=my-cluster \
  --region=us-central1 \
  --instance-type=PRIMARY \
  --cpu-count=4
```

### PSA Networking Requirement

AlloyDB requires **Private Service Access (PSA)** — a peered VPC range allocated for Google-managed services. Client VMs must be in the same VPC (or a connected VPC) to reach the instance IP.

```bash
# Allocate PSA range (one-time per VPC)
gcloud compute addresses create google-managed-services-default \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=20 \
  --network=default

# Create the peering
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-default \
  --network=default
```

### AlloyDB vs Cloud SQL

| Aspect | AlloyDB | Cloud SQL |
|--------|---------|-----------|
| Engine | PostgreSQL-compatible only | PostgreSQL, MySQL, SQL Server |
| Performance | ~4× higher throughput (columnar engine, shared memory cache) | Standard managed RDBMS |
| HA | Auto-failover < 60 s, cross-zone | Regional replica, ~60 s failover |
| Pricing | Higher; compute + storage separate | Instance + storage (simpler) |
| Best for | High-throughput OLTP, mixed OLTP/OLAP | General-purpose managed SQL |

---

## Secret Manager Patterns

### Diff-Based Updates

Avoid creating unnecessary secret versions. Compare the current value before adding a new version.

```bash
# Read existing value
CURRENT=$(gcloud secrets versions access latest --secret="my-secret" 2>/dev/null || echo "")

NEW_VALUE="new-password-here"

if [ "$CURRENT" != "$NEW_VALUE" ]; then
  echo -n "$NEW_VALUE" | gcloud secrets versions add my-secret --data-file=-
  echo "Secret updated."
else
  echo "Secret unchanged, skipping version creation."
fi
```

### Common Access Patterns

```bash
# Access the latest version
gcloud secrets versions access latest --secret="my-secret"

# Access a specific version
gcloud secrets versions access 3 --secret="my-secret"

# List versions
gcloud secrets versions list my-secret

# Create a new secret
echo -n "my-value" | gcloud secrets create my-secret \
  --data-file=- \
  --replication-policy=automatic
```

---

## IAM Workload Identity

Workload Identity lets GKE or Cloud Run workloads impersonate a GCP service account without key files.

### Annotation + Binding Chain

```bash
# 1. Create a GCP Service Account (GSA)
gcloud iam service-accounts create my-app-sa \
  --display-name="My App SA"

# 2. Grant required roles to the GSA
gcloud projects add-iam-policy-binding MY_PROJECT \
  --member="serviceAccount:my-app-sa@MY_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 3. Allow the Kubernetes Service Account (KSA) to impersonate the GSA
gcloud iam service-accounts add-iam-policy-binding \
  my-app-sa@MY_PROJECT.iam.gserviceaccount.com \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:MY_PROJECT.svc.id.goog[NAMESPACE/KSA_NAME]"

# 4. Annotate the KSA
kubectl annotate serviceaccount KSA_NAME \
  --namespace=NAMESPACE \
  iam.gke.io/gcp-service-account=my-app-sa@MY_PROJECT.iam.gserviceaccount.com
```

### Service Account Impersonation (CLI)

```bash
# Impersonate a GSA from a user or another SA
gcloud storage ls \
  --impersonate-service-account=my-app-sa@MY_PROJECT.iam.gserviceaccount.com

# Generate a short-lived token
gcloud auth print-access-token \
  --impersonate-service-account=my-app-sa@MY_PROJECT.iam.gserviceaccount.com
```

---

## VPC Networking

### PSA Ranges

See AlloyDB section above. PSA is also required for Cloud SQL private IP and Memorystore.

### Cloud NAT / Router

Cloud NAT allows VMs without external IPs to reach the internet.

```bash
# Create a Cloud Router
gcloud compute routers create my-router \
  --region=us-central1 \
  --network=default

# Attach Cloud NAT
gcloud compute routers nats create my-nat \
  --router=my-router \
  --region=us-central1 \
  --auto-allocate-nat-external-ips \
  --nat-all-subnet-ip-ranges
```

### Firewall Rules

```bash
# IAP TCP tunneling (SSH/RDP via IAP)
gcloud compute firewall-rules create allow-iap-ssh \
  --network=default \
  --allow=tcp:22 \
  --source-ranges=35.235.240.0/20 \
  --description="Allow SSH via IAP"

# GCP load balancer health checks
gcloud compute firewall-rules create allow-health-checks \
  --network=default \
  --allow=tcp \
  --source-ranges=130.211.0.0/22,35.191.0.0/16 \
  --description="Allow GCP health check probers"
```

| Purpose | CIDR |
|---------|------|
| IAP TCP forwarding | `35.235.240.0/20` |
| GCP health check probers | `130.211.0.0/22`, `35.191.0.0/16` |

---

## Cloud Batch

Cloud Batch is a fully managed service for batch and HPC workloads. It provisions, schedules, and autoscales VMs (including Spot/preemptible) without managing a cluster.

**When to use Cloud Batch vs GKE:**

| Aspect | Cloud Batch | GKE |
|--------|-------------|-----|
| Workload type | Batch jobs, array jobs, MPI | Long-running services, microservices |
| Cluster management | None (fully managed) | Cluster lifecycle managed by operator |
| Spot/preemptible | Built-in, first-class | Node pool configuration |
| GPU / HPC support | A100/H100, HPC VM families | Any accelerator, custom node pools |
| Scheduling | Queue-based, job arrays | Kubernetes scheduler |

```bash
# Submit a simple batch job from JSON spec
gcloud batch jobs submit my-job \
  --location=us-central1 \
  --config=job.json
```

---

## References Index

- **[IAM Guide](references/iam.md)** - Service accounts, role bindings, Workload Identity, and IAM best practices.

## Cross-References

- **Gemini CLI Extensions org**: <https://github.com/gemini-cli-extensions> — community-built Gemini CLI extensions for GCP services and tooling.

## Documentation & References

- **SDK Cheat Sheet**: `gcloud cheat-sheet`
- **Core Services List**: [Google Cloud Products](https://cloud.google.com/products)
- **CLI Reference**: [gcloud CLI docs](https://cloud.google.com/sdk/gcloud/reference)

## Official References

- <https://docs.cloud.google.com/>
- <https://docs.cloud.google.com/sdk/gcloud/reference>
- <https://cloud.google.com/sdk/gcloud/reference/run/deploy>
- <https://docs.cloud.google.com/sdk/docs/authorizing>
- <https://cloud.google.com/artifact-registry/docs/transition/transition-from-gcr>
- <https://cloud.google.com/vertex-ai/generative-ai/docs/migrate/migrate-palm-to-gemini>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [GCP Scripting](https://github.com/cofin/flow/blob/main/templates/styleguides/cloud/gcp_scripting.md)
- [Bash](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/bash.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
