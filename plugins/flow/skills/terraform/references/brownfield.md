# Brownfield Adoption

## Goal

Bring existing infrastructure under Terraform control without accidental replacement, giant one-shot imports, or unreadable generated code.

## Brownfield Sequence

1. **Choose the target boundary first**
   - Decide which root module and state should own the existing resources.
   - Do not import first and figure out boundaries later.

2. **Inventory the existing infrastructure**
   - Confirm resource IDs, project/region scope, and hidden dependencies.
   - For GCP, bulk export can accelerate discovery.

3. **Export when it helps**

Google Cloud can bulk-export supported resources to Terraform HCL:

```bash
gcloud beta resource-config bulk-export \
  --project=PROJECT_ID \
  --resource-format=terraform \
  --path=tf-export
```

Treat exported code as discovery material or a starting scaffold, not finished production code.

1. **Add import intent explicitly**

HashiCorp's recommended modern workflow is to use `import` blocks plus a destination resource address.

Example pattern:

```hcl
import {
  to = google_compute_network.shared
  id = "projects/PROJECT_ID/global/networks/NETWORK_NAME"
}

resource "google_compute_network" "shared" {
  name                    = "NETWORK_NAME"
  auto_create_subnetworks = false
}
```

1. **Generate configuration when useful**

If you only wrote `import` blocks, Terraform can generate resource configuration:

```bash
terraform plan -generate-config-out=generated.tf
```

Review that file carefully. Normalize naming, variables, outputs, and layout before accepting it.

1. **Refactor without churn**

Once the imported resources are stable, move them into the final module structure using `moved` blocks.

Example pattern:

```hcl
moved {
  from = google_compute_network.shared
  to   = module.network.google_compute_network.main
}
```

Use `moved` blocks for:

- renaming a resource
- renaming a module call
- moving a resource into or out of a module
- splitting a larger module into smaller ones

1. **Split only after stabilization**

If a legacy stack is huge, import it into a temporary-but-readable root first, validate ownership, and then split it with `moved` blocks. Avoid doing initial import and multi-root decomposition in the same uncontrolled step.

## Practical GCP Advice

- Bulk export only the resource types you need when a full project export is too noisy.
- Keep shared networking, project/bootstrap, and workload services in separate roots when ownership differs.
- Prefer importing live IAM and networking resources before changing semantics.
- Document every imported ID and the reason the chosen root owns it.

## Anti-Patterns

- Editing the state file directly to bypass proper imports
- Accepting generated HCL without cleanup
- Importing multiple teams' infrastructure into one state
- Using import as a shortcut to justify destructive refactors
