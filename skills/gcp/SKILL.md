---
name: gcp
description: "Expert knowledge for Google Cloud Platform: Core services, `gcloud` CLI scripting patterns, and automation best practices."
---

# Google Cloud Platform (GCP) Skill

## Service Overview (2025)

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

## `gcloud` CLI & Scripting

### Configuration & Auth

Avoid interactive prompts in scripts.

```bash
# Production/CI: Use Service Account Key or Workload Identity
gcloud auth activate-service-account --key-file=key.json

# Local Dev: User Login
gcloud auth login
gcloud config set project MY_PROJECT_ID
```

### Scripting Best Practices

#### 1. Structured Output

Never parse default text output. Use `--format` (json/yaml) and `--filter`.

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

#### 2. Deterministic Filters

Flatten complex resources to find what you need.

```bash
# Find latest revision of a service
gcloud run revisions list \
  --service=my-service \
  --sort-by="~metadata.creationTimestamp" \
  --limit=1 \
  --format="value(metadata.name)"
```

#### 3. Quiet Mode

Suppress "updates available" warnings and prompts.

```bash
export CLOUDSDK_CORE_DISABLE_PROMPTS=1
gcloud ... --quiet
```

## Automation Patterns

### 1. Cloud Run Deployment

Standard pattern for deploying containers.

```bash
gcloud run deploy my-service \
  --image gcr.io/my-project/my-image:tag \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DEBUG=true,DB_HOST=10.0.0.2"
```

### 2. Secret Management

Access secrets securely (requires Secret Manager API).

```bash
# Mount as volume in Cloud Run (Preferred)
gcloud run deploy ... --set-secrets="/secrets/db=my-db-secret:latest"

# Access via CLI (for ops scripts)
gcloud secrets versions access latest --secret="my-secret"
```

## Documentation & References

- **SDK Cheat Sheet**: `gcloud cheat-sheet`
- **Core Services List**: [Google Cloud Products](https://cloud.google.com/products)
- **CLI Reference**: [gcloud CLI docs](https://cloud.google.com/sdk/gcloud/reference)
