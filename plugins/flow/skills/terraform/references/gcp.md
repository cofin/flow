# GCP Terraform Patterns

## Authentication Order

Use the most secure low-admin path available:

1. **Local development:** Application Default Credentials (ADC)
2. **Privileged local workflows:** service account impersonation
3. **CI on Google Cloud:** attached user-managed service account
4. **CI outside Google Cloud:** Workload Identity Federation
5. **Service account keys:** last resort only

Google documents ADC as the recommended way to authenticate Terraform on Google Cloud. For external CI, Google recommends Workload Identity Federation instead of downloading service account keys.

## Sensitive Data Handling

Terraform state and saved plan files can contain secrets such as initial passwords, tokens, or provider credentials. Treat both as sensitive artifacts.

Practical defaults:

- keep state and plan files out of Git
- keep plan JSON out of public or weakly protected artifact storage
- prefer Secret Manager or another external secret source over plaintext secrets in `terraform.tfvars`
- mark user-facing secret inputs with `sensitive = true`
- use `ephemeral = true` or write-only arguments when the provider/resource supports them and the value should not persist in state or plan files

Example variable:

```hcl
variable "database_password" {
  type        = string
  sensitive   = true
  ephemeral   = true
  description = "Short-lived password passed into a write-only argument or provider config"
}
```

## Local Development

User-account ADC:

```bash
gcloud auth application-default login
gcloud config set project PROJECT_ID
```

Service account impersonation for local ADC:

```bash
gcloud auth application-default login \
  --impersonate-service-account=terraform-admin@PROJECT_ID.iam.gserviceaccount.com
```

## Provider and Backend Skeleton

```hcl
terraform {
  required_version = ">= 1.10.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0" # Pin to a current minor series intentionally.
    }
  }

  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}
```

## Multiple Provider Configurations

Use explicit aliases when the root spans multiple projects, regions, or trust boundaries.

Example:

```hcl
provider "google" {
  project = var.service_project_id
  region  = var.region
}

provider "google" {
  alias   = "host"
  project = var.host_project_id
  region  = var.region
}

resource "google_compute_shared_vpc_service_project" "attachment" {
  provider        = google.host
  host_project    = var.host_project_id
  service_project = var.service_project_id
}
```

If a resource requires beta-only provider features, add a `google-beta` provider configuration deliberately rather than silently switching the whole root.

Prefer a dedicated GCS state bucket with a unique prefix per root and environment. Example:

```hcl
backend "gcs" {
  bucket = "org-terraform-state"
  prefix = "product-a/prod/api-service"
}
```

## CI Guidance

Google's operations guidance recommends executing Terraform through automated tooling and using service account credentials inherited from the execution environment.

Practical defaults:

- Cloud Build: use the build service account or a dedicated worker SA
- GKE runners: use Workload Identity / attached workload identity
- GitHub Actions or other external CI: use Workload Identity Federation

Avoid downloaded JSON keys unless there is no viable alternative.

## API Enablement

Manage required Google APIs intentionally.

- Use `google_project_service` for project-level API enablement.
- Keep bootstrap or project-factory concerns separate from application service roots when lifecycle coupling would be confusing.
- Do not scatter API enablement across many unrelated roots.

## Version Pinning

Google recommends pinning providers to minor versions in root modules. Review those pins regularly rather than letting them stagnate forever.

Pin reusable Google modules too. Examples:

```hcl
module "gke" {
  source  = "terraform-google-modules/kubernetes-engine/google//modules/private-cluster"
  version = "~> 31.0" # Replace with the current compatible minor series.
}
```

```hcl
module "project" {
  source  = "terraform-google-modules/project-factory/google"
  version = "~> 18.0" # Replace with the current compatible minor series.
}
```

## Remote State and Outputs

Expose outputs from live roots that other roots legitimately need.

```hcl
output "project_id" {
  description = "Project ID for downstream stacks"
  value       = module.project.project_id
}
```

Consume only root-level outputs from other states. Do not couple one root to another root's internal resource addresses.

## Policy Validation

For shared or sensitive Google Cloud infrastructure, consider validating plans with `gcloud beta terraform vet`.

Typical flow:

```bash
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json
gcloud beta terraform vet tfplan.json --policy-library=. --format=json
```

This is especially useful for IAM, org policy, and compliance-sensitive stacks.

## Service-Specific References

Once the Terraform structure is stable, reuse existing service examples:

- Cloud Run: [../../cloud-run/references/terraform.md](../../cloud-run/references/terraform.md)
- GKE: [../../gke/references/terraform.md](../../gke/references/terraform.md)
