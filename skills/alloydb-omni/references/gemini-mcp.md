# Gemini CLI and MCP Toolbox

## Agent Integration Order

1. Gemini extension path
2. MCP Toolbox path for other agents or shared MCP setups
3. Manual Omni deployment plus `psql` fallback

This keeps the skill usable across hosts instead of tying it to Gemini only.

## Preferred Path for Gemini

For AlloyDB Omni, use the dedicated Gemini CLI extension when available:

```bash
gemini extensions install https://github.com/gemini-cli-extensions/alloydb-omni --auto-update
gemini extensions config alloydb-omni --scope workspace
```

The dedicated Omni extension exposes workspace-configured host/user/password settings and is a better default than treating every Omni workflow as generic PostgreSQL.

## Environment Configuration

```bash
export ALLOYDB_OMNI_HOST="<database-host>"
export ALLOYDB_OMNI_PORT="<database-port>"
export ALLOYDB_OMNI_DATABASE="<database-name>"
export ALLOYDB_OMNI_USER="<database-user>"
export ALLOYDB_OMNI_PASSWORD="<database-password>"
export ALLOYDB_OMNI_QUERY_PARAMS="<optional-query-string>"
```

Notes:

- Gemini CLI should be `v0.6.0+`.
- Load these values from a `.env` file when possible.
- Restart Gemini when switching databases or credentials.
- Keep this config at workspace scope by default.

## MCP Toolbox Fallback

For other LLMs or shared MCP setups, use the official AlloyDB Omni prebuilt config via Toolbox.

```bash
gemini extensions install https://github.com/gemini-cli-extensions/mcp-toolbox --auto-update
```

For reusable workspace automation, generate project-local skills:

```bash
toolbox --prebuilt alloydb-omni skills-generate \
  --name alloydb-omni-optimize \
  --toolset optimize \
  --description "AlloyDB Omni optimization skill" \
  --output-dir .agents/skills
```

If Toolbox is unavailable, fall back to the Docker, Kubernetes, RPM, and performance references in this skill.
