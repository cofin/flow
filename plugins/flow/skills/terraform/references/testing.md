# Terraform Testing and Delivery

## Minimum Validation Pipeline

Use this baseline for any meaningful Terraform change:

```bash
terraform fmt -check -recursive
terraform init
terraform validate
terraform plan -out=tfplan
```

For reusable modules that should validate without touching a real backend:

```bash
terraform init -backend=false
terraform validate
```

HashiCorp documents `terraform validate` as safe to run automatically and frequently.

## Saved Plans

Google's operations guidance recommends always generating a plan first and saving it to an output file before approval and execution.

Typical sequence:

```bash
terraform plan -out=tfplan
terraform show tfplan
terraform apply tfplan
```

Do not skip the saved-plan step for shared or production roots.
Treat both `tfplan` and any derived JSON output as sensitive artifacts.

## Automated Pipelines

Google recommends executing Terraform through automated tooling for consistent execution context.

Default delivery model:

1. format and static validation
2. module tests or targeted integration tests
3. saved plan artifact
4. optional policy validation
5. human approval
6. apply from CI

## Module and Integration Testing

Google's testing guidance highlights:

- static analysis with `terraform validate`
- integration testing for modules in isolated test environments
- staged execution for faster iteration

Officially referenced testing frameworks include:

- Google's blueprint testing framework
- Terratest
- Kitchen-Terraform

## Built-In `terraform test`

HashiCorp's `terraform test` command is useful for module authors and can also validate root modules.

Typical structure:

```text
project/
├── main.tf
├── terraform.tf
├── variables.tf
├── outputs.tf
└── tests/
    ├── validations.tftest.hcl
    └── outputs.tftest.hcl
```

Basic usage:

```bash
terraform test
terraform test -filter=tests/validations.tftest.hcl
```

Important caution: `terraform test` can create real infrastructure. Use dedicated test projects or accounts and confirm cleanup.

## Policy Checks

When using Google Cloud policy validation:

```bash
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json
gcloud beta terraform vet tfplan.json --policy-library=. --format=json
```

Use policy validation for shared infrastructure, IAM-sensitive changes, org-level controls, or regulated environments.

## Review Standards

Before an apply is approved, reviewers should be able to answer:

- Which root module and state are changing?
- What will be created, modified, or destroyed?
- Is the environment boundary correct?
- Are provider/module pin changes intentional?
- Are imported or moved resources documented?
- Was policy validation required, and did it pass?
