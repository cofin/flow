---
name: gcp
description: "Expert knowledge for Google Cloud Platform: Core services, `gcloud` CLI scripting patterns, and automation best practices."
---

# Google Cloud Platform (GCP) Skill

## Service Overview (2026)

### Core Services

- **Compute**
  - **Cloud Run**: Serverless containers; strong default for stateless services and jobs.
  - **GKE**: Managed Kubernetes for advanced orchestration and platform control.
  - **Compute Engine**: VMs when you need host-level control.
- **Data and storage**
  - **Cloud Storage**: Object storage.
  - **Cloud SQL**: Managed PostgreSQL / MySQL / SQL Server.
  - **BigQuery**: Serverless analytics warehouse.
  - **Firestore**: NoSQL document database.
- **AI/ML**
  - **Vertex AI**: Managed AI platform with Gemini model access, training, and serving.

## `gcloud` CLI & Scripting

### Configuration & Auth

Prefer short-lived credentials in automation. Avoid long-lived service account keys unless no alternative exists.

```bash
# CI/external workloads: Workload Identity Federation (preferred to key files)
# (cred file generated via `gcloud iam workload-identity-pools create-cred-config`)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/wif-cred.json

# Local dev: user login for gcloud
gcloud auth login

# Optional: impersonate a service account for command execution
gcloud config set auth/impersonate_service_account SA_NAME@PROJECT_ID.iam.gserviceaccount.com
gcloud config set project PROJECT_ID
```

### Scripting Best Practices

#### 1. Structured output

Never parse human-readable default output. Use `--format`, `--filter`, and projections.

```bash
# Avoid
gcloud compute instances list | grep RUNNING

# Better: machine-readable
gcloud compute instances list --format="json"

# Better: single projected value
gcloud run services describe my-service --region=us-central1 --format="value(status.url)"
```

#### 2. Deterministic selection

Sort and limit explicitly when selecting one resource.

```bash
# Find latest revision of a service
gcloud run revisions list \
  --service=my-service \
  --sort-by="~metadata.creationTimestamp" \
  --limit=1 \
  --format="value(metadata.name)"
```

#### 3. Non-interactive mode

Use non-interactive flags in CI and scripts.

```bash
export CLOUDSDK_CORE_DISABLE_PROMPTS=1
gcloud run services list --quiet
```

## Automation Patterns

### 1. Cloud Run deploy (Artifact Registry)

```bash
gcloud run deploy my-service \
  --image us-central1-docker.pkg.dev/my-project/my-repo/my-image:tag \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="APP_ENV=prod"
```

Notes:
- Prefer Artifact Registry image URLs (`LOCATION-docker.pkg.dev/...`).
- Legacy Container Registry was deprecated and shut down in 2025.

### 2. Secret Manager with Cloud Run

Use Cloud Run secret flags instead of embedding secrets in env values.

```bash
# Env var mapping
gcloud run deploy my-service \
  --image us-central1-docker.pkg.dev/my-project/my-repo/my-image:tag \
  --region us-central1 \
  --update-secrets="DB_PASSWORD=my-db-password:latest"

# Direct access for operational scripts
gcloud secrets versions access latest --secret="my-secret"
```

## Where to Learn More (Official)

- Google Cloud product catalog: https://cloud.google.com/products
- gcloud CLI reference root: https://docs.cloud.google.com/sdk/gcloud/reference
- gcloud formats and filters:
  - https://docs.cloud.google.com/sdk/gcloud/reference/topic/formats
  - https://docs.cloud.google.com/sdk/gcloud/reference/topic/filters
- Cloud Run deployment:
  - https://docs.cloud.google.com/run/docs/deploying
  - https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy
- Cloud Run + Secret Manager:
  - https://docs.cloud.google.com/run/docs/configuring/services/secrets
- Authentication and identity:
  - https://docs.cloud.google.com/docs/authentication/use-service-account-impersonation
  - https://docs.cloud.google.com/iam/docs/workload-identity-federation
  - https://cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys
- Artifact Registry and GCR transition:
  - https://cloud.google.com/artifact-registry/docs/transition/transition-from-gcr
- Vertex AI model migration:
  - https://cloud.google.com/vertex-ai/generative-ai/docs/migrate/migrate-palm-to-gemini

## Quick References

- SDK cheat sheet: `gcloud cheat-sheet`
- Keep this skill focused on GCP-specific workflows, edge cases, and integration details.
