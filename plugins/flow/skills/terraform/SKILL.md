---
name: terraform
description: "Use when creating, adopting, refactoring, or operating Terraform, *.tf files, .terraform.lock.hcl, terragrunt.hcl, root modules, backends, state, workspaces, imports, CI plan/apply, tests, or policy checks."
---

# Terraform

## Overview

Use this skill to keep Terraform work small-state, reviewable, and brownfield-safe.

This repo should treat Terraform as four separate concerns:

1. **Place** Terraform in the right part of the repo.
2. **Provision** new infrastructure with clear root-module boundaries.
3. **Adopt** existing infrastructure without taking unsafe shortcuts.
4. **Operate** Terraform through validated plans, CI, and policy checks.

For this repo family, default to **brownfield embedding** inside an existing product repo unless the user explicitly wants a dedicated infrastructure repository.

## Quick Reference

| Decision | Default | Avoid |
|---|---|---|
| Brownfield placement | `infra/terraform/` inside the existing repo | Mixing Terraform into `src/` or app runtime folders |
| Environment model | Separate directories and separate state per env/root | Using CLI workspaces for `dev` / `stage` / `prod` |
| State size | One root module per deployable unit or boundary | Giant multi-service roots |
| GCP backend | GCS remote state | Local state for shared environments |
| Local auth | ADC | Long-lived service account keys |
| CI auth | Attached service account on GCP, otherwise WIF | Downloaded JSON keys when avoidable |
| Sensitive values | Treat state and plan artifacts as sensitive; prefer Secret Manager plus `sensitive` / `ephemeral` patterns when supported | Hardcoding secrets or committing plan/state artifacts |
| Brownfield adoption | Export/import, review, then refactor with `moved` blocks | Hand-editing state to “make it fit” |

## Operating Lanes

### Lane 1: Repo and State Design

- Keep Terraform in a clearly scoped infrastructure area.
- Prefer `infra/terraform/` for brownfield repos.
- Keep reusable modules separate from live environment roots.
- Keep each root module small enough that reviewers can understand a plan.

### Lane 2: Greenfield Provisioning

- Start with a small root module and a reusable module boundary only where reuse is real.
- Pin provider and module versions.
- Check in `.terraform.lock.hcl`.

### Lane 3: Brownfield Adoption

- Inventory what already exists.
- Export or import existing resources into Terraform.
- Normalize the generated or imported configuration.
- Refactor with `moved` blocks instead of destructive rename/recreate cycles.

### Lane 4: Day-2 Operations

- Run `fmt`, `validate`, saved `plan`, and policy checks before `apply`.
- Prefer CI-mediated `plan` and `apply`, especially for shared environments.
- Upgrade versions intentionally and review lockfile drift.

<workflow>

## Workflow

### Step 1: Choose Repo Placement

Use the smallest layout that preserves clear ownership.

- **Brownfield application repo:** put Terraform under `infra/terraform/`.
- **Dedicated infra repo:** keep the same internal split of `modules/` and live environment roots.
- **Service-specific IaC:** place service roots under `infra/terraform/environments/<env>/<service>/`.

Read [references/layout.md](references/layout.md) before creating directories.

### Step 2: Define Root-Module Boundaries

A root module is a state boundary. Treat it as an operational boundary too.

- Split by application, shared platform service, or blast-radius boundary.
- Prefer separate roots for shared networking, project/bootstrap, and app-service stacks.
- Keep unrelated systems out of the same state even if they deploy together.

### Step 3: Establish Backend and Auth

For GCP, default to:

- **Local development:** ADC
- **Privileged local work:** service account impersonation
- **CI on Google Cloud:** attached service account
- **CI outside Google Cloud:** Workload Identity Federation
- **Remote state:** GCS backend per root/environment

Read [references/gcp.md](references/gcp.md) before writing provider or backend configuration.

If the root spans multiple projects, regions, or beta-only resources, define explicit provider aliases instead of overloading one default `google` provider configuration.

### Step 3.5: Handle Sensitive Values Early

Treat Terraform state files, saved plan files, and plan JSON as sensitive artifacts.

- Keep state and plan artifacts out of Git.
- Prefer Secret Manager or another external secret source over plaintext secrets in `.tfvars`.
- Use `sensitive = true` for inputs and outputs that must be redacted.
- Use `ephemeral = true` or write-only arguments when the provider/resource supports them and the value should stay out of state and plan files entirely.

### Step 4: Pick the Environment Model

Use separate directories and separate state for `dev`, `stage`, and `prod`.

Use Terraform CLI workspaces only when all of the following are true:

- the configuration is the same shape in every instance
- credentials and approvals are the same
- the backend is shared intentionally
- the instances are peers, not separate systems

If any of those conditions are false, do not use CLI workspaces as the primary environment model.

### Step 5: Implement and Validate

Before proposing an `apply`, run the low-risk checks first:

1. `terraform fmt`
2. `terraform init`
3. `terraform validate`
4. `terraform plan -out=tfplan`
5. `terraform show -json tfplan > tfplan.json` when policy tooling or machine review is needed
6. `terraform test` when the module or root justifies it

Use [references/testing.md](references/testing.md) for the validation pipeline.

### Step 6: Brownfield Adoption Path

When a system already exists:

1. Decide the target root-module boundary before importing anything.
2. Export existing GCP resources if that accelerates discovery.
3. Add `import` blocks or targeted imports for the selected boundary.
4. Generate configuration when helpful, but treat it as a scaffold.
5. Refactor into the desired module shape.
6. Use `moved` blocks to preserve state history during renames or splits.

Use [references/brownfield.md](references/brownfield.md) for the exact flow.

### Step 7: Connect Service-Specific Patterns

After the Terraform structure is sound, pull in service-specific references:

- Cloud Run examples: [../cloud-run/references/terraform.md](../cloud-run/references/terraform.md)
- GKE examples: [../gke/references/terraform.md](../gke/references/terraform.md)

</workflow>

<guardrails>

## Guardrails

- **Do not use CLI workspaces for system decomposition** or for environments with separate credentials or approvals.
- **Do not put unrelated services in one state** just because a single PR touches them.
- **Do not hand-edit Terraform state** unless it is a documented break-glass recovery.
- **Do not normalize brownfield infrastructure by deleting and recreating it** when import and refactor paths exist.
- **Do not treat exported or generated HCL as production-ready** until it is cleaned up and reviewed.
- **Do not rely on service account keys by default on GCP** when ADC, impersonation, or Workload Identity Federation are available.
- **Do not treat remote state as non-sensitive**. State files and saved plans can contain secrets, tokens, and generated credentials.
- **Do not skip `.terraform.lock.hcl` in root modules** that will be shared or reviewed.
- **Do not hide destructive changes inside apply-only workflows**. Save and review the plan first.
- **Do not introduce Terragrunt as the default architecture** unless the repo already standardized on it. Plain Terraform is the baseline.
- **Do not let helper scripts become hidden infrastructure dependencies**. Prefer provider resources and documented modules first.
- **Do not leave stateful resources without lifecycle protection**. Use `prevent_destroy` and provider-specific deletion protection where the platform supports them.

</guardrails>

<validation>

## Validation Checkpoint

Before claiming a Terraform change is ready, verify:

- [ ] the repo layout keeps Terraform out of application runtime folders
- [ ] each root module has a clear ownership and state boundary
- [ ] environment separation uses directories/state, or workspace use is explicitly justified
- [ ] backend and authentication strategy are documented
- [ ] sensitive inputs, state, and plan artifacts are handled as secrets
- [ ] provider aliases or `google-beta` configuration are explicit when multi-project, multi-region, or beta-only resources are involved
- [ ] provider and module versions are pinned intentionally
- [ ] `.terraform.lock.hcl` is committed when the root is meant to be versioned
- [ ] `terraform fmt`, `terraform validate`, and a saved `terraform plan -out=...` were run
- [ ] stateful resources use lifecycle protection or an explicitly documented exception
- [ ] brownfield imports, generated config, and `moved` blocks are documented when applicable
- [ ] policy validation and module tests were considered for shared or sensitive infrastructure

</validation>

<example>

## Example

Brownfield application repo layout:

```text
repo/
├── src/
├── tests/
├── .agents/
└── infra/
    └── terraform/
        ├── modules/
        │   ├── project-services/
        │   ├── network/
        │   └── cloud-run-service/
        └── environments/
            ├── dev/
            │   ├── shared-network/
            │   └── api-service/
            ├── stage/
            │   ├── shared-network/
            │   └── api-service/
            └── prod/
                ├── shared-network/
                └── api-service/
```

Minimal root files:

```text
api-service/
├── backend.tf
├── main.tf
├── providers.tf
├── terraform.tf
├── terraform.tfvars
├── variables.tf
├── outputs.tf
└── README.md
```

GCP root skeleton:

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

module "service" {
  source     = "../../modules/cloud-run-service"
  project_id = var.project_id
  region     = var.region
  name       = var.name
}
```

</example>

---

## References Index

- **[Layout and Workspaces](references/layout.md)**
  - Brownfield repo placement, root-module boundaries, directory conventions, and when not to use CLI workspaces.
- **[GCP Terraform Patterns](references/gcp.md)**
  - ADC, impersonation, WIF, GCS backends, API enablement, module pinning, and policy validation on Google Cloud.
- **[Brownfield Adoption](references/brownfield.md)**
  - Export, import blocks, generated configuration, and refactoring with `moved` blocks.
- **[Testing and Delivery](references/testing.md)**
  - `fmt`, `validate`, saved plans, `terraform test`, CI, and policy checks.

## Official References

- <https://docs.cloud.google.com/docs/terraform/best-practices/general-style-structure>
- <https://docs.cloud.google.com/docs/terraform/best-practices/root-modules>
- <https://docs.cloud.google.com/docs/terraform/best-practices/operations>
- <https://docs.cloud.google.com/docs/terraform/best-practices/testing>
- <https://docs.cloud.google.com/docs/terraform/authentication>
- <https://docs.cloud.google.com/docs/terraform/resource-management/export>
- <https://docs.cloud.google.com/docs/terraform/resource-management/import>
- <https://docs.cloud.google.com/docs/terraform/policy-validation/quickstart>
- <https://developer.hashicorp.com/terraform/language/style>
- <https://developer.hashicorp.com/terraform/language/state/workspaces>
- <https://developer.hashicorp.com/terraform/language/import>
- <https://developer.hashicorp.com/terraform/language/modules/develop/refactoring>
