---
name: railway
description: Expert knowledge for Railway deployment platform. Use when deploying applications, configuring services, managing databases, or troubleshooting Railway deployments.
---

# Railway Deployment Platform Skill

Verified against official Railway docs on 2026-03-02.

## High-signal rules

- Serverless (formerly App Sleeping) marks a service inactive after 10+ minutes without outbound packets.
- Outbound traffic includes DB connections, telemetry, and private-network traffic.
- Wake-up is triggered by traffic from the internet or from another service over Railway private networking.
- For non-HTTP workers/consumers, disable Serverless (`sleepApplication: false`) to avoid idle stalls.
- Healthchecks are HTTP-200 based for deploy readiness; do not set HTTP healthchecks on services with no HTTP endpoint.
- Railway injects `PORT` at runtime; apps should bind to `PORT`, not a hardcoded port.

## Config-as-code essentials

- Use `railway.toml` or `railway.json` with schema `https://railway.com/railway.schema.json`.
- Config in code overrides dashboard values for that deployment; it does not update dashboard settings.
- Per-service config file path can be set in service settings.
- Config file path is absolute from repo root (for example `/backend/railway.toml`).

Example:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "sleepApplication": false,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

## CLI quick reference

```bash
# Auth + context
railway login
railway whoami
railway link
railway status --json

# Services
railway add --service "web"
railway add --database postgres

# Variables
railway variable list --kv
railway variable set DATABASE_URL='${{Postgres.DATABASE_URL}}'
railway variable set REDIS_URL='${{Redis.REDIS_URL}}'
railway variable set APP_URL='https://${{RAILWAY_PUBLIC_DOMAIN}}'
railway variable set CONFIG_VALUE=123 --skip-deploys

# Deploy
railway up
railway up --detach
railway up --ci
railway logs
railway redeploy
railway domain

# Local run with Railway env
railway run npm run dev
railway run python manage.py migrate
```

## Multi-service guidance (web + worker)

- Web service: may use Serverless if cold-start tolerance is acceptable.
- Worker/queue/cron service: disable Serverless, disable HTTP healthcheck, use restart policy.
- Use reference variables for shared infra:
`${{Postgres.DATABASE_URL}}`, `${{Redis.REDIS_URL}}`, `${{shared.SECRET_KEY}}`.

## Troubleshooting checklist

- Sleeping unexpectedly: check outbound traffic patterns and Serverless setting.
- Worker not processing jobs: verify Serverless is off and queue/Redis variables resolve correctly.
- Deploy not picking config: verify service config path and absolute path from repo root.
- Traffic issues after deploy: verify app listens on `PORT` and healthcheck endpoint returns `200`.

## Official learn-more links

- Docs home: https://docs.railway.com/
- CLI overview: https://docs.railway.com/cli
- `railway up`: https://docs.railway.com/cli/up
- `railway variable`: https://docs.railway.com/cli/variable
- `railway add`: https://docs.railway.com/cli/add
- `railway domain`: https://docs.railway.com/cli/domain
- `railway redeploy`: https://docs.railway.com/cli/redeploy
- Deploying with CLI: https://docs.railway.com/cli/deploying
- Using variables: https://docs.railway.com/variables
- Variables reference: https://docs.railway.com/reference/variables
- Serverless (App Sleeping): https://docs.railway.com/reference/app-sleeping
- Healthchecks: https://docs.railway.com/reference/healthchecks
- Config as code guide: https://docs.railway.com/deploy/config-as-code
- Config as code reference: https://docs.railway.com/reference/config-as-code
