# Terraform Layout and Workspaces

## Default Brownfield Placement

When adding Terraform to an existing application repository, default to:

```text
infra/terraform/
```

Keep application code and Terraform code separate. Do not spread Terraform across `src/`, deployment scripts, or random service folders unless the repo already has an explicit IaC convention that must be preserved.

## Recommended Repository Shapes

### Brownfield Product Repo

```text
repo/
├── .agents/
├── src/
├── docs/
└── infra/
    └── terraform/
        ├── modules/
        └── environments/
            ├── dev/
            ├── stage/
            └── prod/
```

### Dedicated Infra Repo

```text
repo/
├── modules/
├── environments/
│   ├── dev/
│   ├── stage/
│   └── prod/
└── docs/
```

## Root Module Boundaries

A root module is both a code boundary and a state boundary.

Prefer one root per:

- application or service
- shared platform dependency such as networking
- environment-specific deployable unit
- approval or credential boundary

Google's root-module guidance recommends keeping a root from growing too large and gives a practical ceiling of about 100 resources, ideally only a few dozen.

## Root Module Files

For live roots, prefer these files:

- `backend.tf`
- `main.tf`
- `providers.tf`
- `terraform.tf`
- `terraform.tfvars`
- `variables.tf`
- `outputs.tf`
- `README.md`

For reusable modules, follow the standard module structure:

- `main.tf`
- `variables.tf`
- `outputs.tf`
- `README.md`
- `examples/`
- optional logical files like `network.tf`, `iam.tf`, `service.tf`

## Protect Stateful Resources

For stateful resources such as databases, enable lifecycle protection by default unless the user explicitly needs a disposable environment.

Example:

```hcl
resource "google_sql_database_instance" "main" {
  name = "primary-instance"

  settings {
    tier = "db-custom-2-7680"
  }

  lifecycle {
    prevent_destroy = true
  }
}
```

If a resource also offers a provider-specific deletion-protection flag, use that too. Document any exception instead of quietly removing the protection.

## Workspaces Versus Directories

| Use case | Prefer directories and separate state | CLI workspaces acceptable |
|---|---|---|
| `dev` / `stage` / `prod` | Yes | No |
| Separate credentials or approval flows | Yes | No |
| Shared backend would be risky | Yes | No |
| Repeated instances of the same config with the same trust boundary | Maybe | Yes |
| Ephemeral peer environments with identical shape | Maybe | Yes |

HashiCorp explicitly warns that CLI workspaces are not appropriate for system decomposition or deployments requiring separate credentials and access controls.

Google's root-module guidance also recommends separate environment directories and says each environment directory should map to the default workspace only.

## Practical Default

Unless the repo already has a justified workspace convention:

- use the default workspace only
- use separate directories for environments
- use separate state for each live root
- avoid `terraform.workspace` conditionals for primary environment logic

## Cross-Configuration Communication

When one root truly depends on another, expose root outputs and consume them via remote state or another explicit integration boundary. Do not reach into another module's internals or duplicate identifiers by hand.
