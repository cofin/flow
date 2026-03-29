---
name: cloud-run
description: "Auto-activate for Cloud Run service.yaml, gcloud run commands. Google Cloud Run serverless platform: Dockerfile, containerized services, Cloud Run Jobs, cold starts, traffic splitting. Use when: deploying containers to Cloud Run, writing Dockerfiles for serverless, or tuning scaling/concurrency."
---

# Google Cloud Run Skill

## Overview

Cloud Run is a fully managed serverless platform for running containerized applications. It automatically scales from zero to N based on incoming requests and charges only for resources used during request processing.

---

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
