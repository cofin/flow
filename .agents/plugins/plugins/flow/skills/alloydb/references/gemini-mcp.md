# Gemini CLI and MCP Toolbox

## Agent Integration Order

1. Gemini extension path
2. MCP Toolbox path for other agents or shared MCP setups
3. Manual `gcloud` + Auth Proxy + `psql` fallback

This keeps the AlloyDB skill usable across hosts instead of coupling it to Gemini only.

## Preferred Path for Gemini

Use the dedicated Gemini CLI extensions for managed AlloyDB:

```bash
gemini extensions install https://github.com/gemini-cli-extensions/alloydb --auto-update
gemini extensions install https://github.com/gemini-cli-extensions/alloydb-observability --auto-update
gemini extensions config alloydb --scope workspace
```

These extensions are backed by MCP Toolbox for Databases, but Gemini CLI users do not need to stand up a separate MCP server first.

## Required Prerequisites

- Gemini CLI `v0.6.0+`
- Application Default Credentials
- IAM roles based on the task:
  - `roles/alloydb.viewer` for read-only discovery
  - `roles/alloydb.client` for SQL access
  - `roles/alloydb.admin` for admin operations
  - `roles/serviceusage.serviceUsageConsumer` for service usage
  - `roles/monitoring.viewer` for observability extension usage

## Environment Configuration

```bash
export ALLOYDB_POSTGRES_PROJECT="<your-gcp-project-id>"
export ALLOYDB_POSTGRES_REGION="<your-alloydb-region>"
export ALLOYDB_POSTGRES_CLUSTER="<your-alloydb-cluster-id>"
export ALLOYDB_POSTGRES_INSTANCE="<your-alloydb-instance-id>"
export ALLOYDB_POSTGRES_DATABASE="<your-database-name>"
export ALLOYDB_POSTGRES_USER="<your-database-user>"         # optional
export ALLOYDB_POSTGRES_PASSWORD="<your-database-password>" # optional
export ALLOYDB_POSTGRES_IP_TYPE="PRIVATE"                    # PRIVATE / PUBLIC / PSC
```

Notes:

- Load these from a `.env` file when possible.
- If using private IP, Gemini CLI must run from the same VPC.
- Connection settings are fixed at session start, so switching instances/databases requires restarting Gemini.
- Prefer IAM-first auth. Treat passwords as a fallback path only.

## MCP Toolbox Fallback

For other LLMs or shared MCP setups, use the official prebuilt Toolbox config:

```bash
gemini extensions install https://github.com/gemini-cli-extensions/mcp-toolbox --auto-update
```

```json
{
  "mcpServers": {
    "alloydb": {
      "command": "./toolbox",
      "args": ["--prebuilt", "alloydb-postgres", "--stdio"],
      "env": {
        "ALLOYDB_POSTGRES_PROJECT": "PROJECT_ID",
        "ALLOYDB_POSTGRES_REGION": "REGION",
        "ALLOYDB_POSTGRES_CLUSTER": "CLUSTER_NAME",
        "ALLOYDB_POSTGRES_INSTANCE": "INSTANCE_NAME",
        "ALLOYDB_POSTGRES_DATABASE": "DATABASE_NAME",
        "ALLOYDB_POSTGRES_USER": "USERNAME",
        "ALLOYDB_POSTGRES_PASSWORD": "PASSWORD",
        "ALLOYDB_POSTGRES_IP_TYPE": "PRIVATE"
      }
    }
  }
}
```

For reusable workspace automation, generate project-local skills instead of rewriting the same prompts:

```bash
toolbox --prebuilt alloydb-postgres skills-generate \
  --name alloydb-monitor \
  --toolset monitor \
  --description "AlloyDB monitoring skill" \
  --output-dir .agents/skills
```

If Toolbox is unavailable, fall back to the manual setup and operations references in this skill.
