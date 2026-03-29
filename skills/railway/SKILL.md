---
name: railway
description: "Auto-activate for railway.toml, railway.json, Procfile. Expert knowledge for Railway deployment platform. Use when deploying applications, configuring services, managing databases, or troubleshooting Railway deployments."
---

# Railway Deployment Platform Skill

## Critical Concepts

### Serverless / App Sleeping

Railway's serverless feature puts services to sleep after 10 minutes of no **outbound** traffic.

**Key Rules:**

- Services wake ONLY on incoming HTTP requests
- Workers/background tasks CANNOT use serverless (no HTTP to wake them)
- Database connections, Redis polling, and telemetry count as outbound traffic (keep service awake)
- `sleepApplication: false` in railway.json disables serverless

**When to disable serverless:**

- Background workers (Celery, SAQ, RQ, Sidekiq)
- Queue processors
- Cron services
- Any service without an HTTP endpoint

### Config-as-Code (railway.json)

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "runtime": "V2",
    "numReplicas": 1,
    "sleepApplication": false,
    "startCommand": "python main.py",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

**Important:** A single `railway.json` in root applies globally to ALL services from the same repo. For service-specific configs:

1. Create separate config files: `railway.app.json`, `railway.worker.json`
2. Configure in Railway dashboard: Settings → Deploy → Config file path
3. Different root directories (monorepo approach)

### Environment Overrides

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "deploy": {
    "startCommand": "npm start"
  },
  "environments": {
    "staging": {
      "deploy": {
        "startCommand": "npm run staging"
      }
    },
    "pr": {
      "deploy": {
        "sleepApplication": true
      }
    }
  }
}
```

## CLI Commands

### Authentication & Project Setup

```bash
# Login
railway login

# Check current user
railway whoami

# Initialize new project
railway init --name "my-project"

# Link to existing project
railway link

# Check project status
railway status
railway status --json
```

### Service Management

```bash
# Add services
railway add --service "Web App"
railway add --database postgres
railway add --database redis

# Link to specific service
railway service link "Web App"

# List services
railway service --json
```

### Environment Variables

```bash
# Set variables (triggers redeploy)
railway variables --set "DATABASE_URL=postgres://..." --set "PORT=3000"

# Set variables without redeploy
railway variables --set "CONFIG_VALUE=123" --skip-deploys

# Set for specific service
railway variables --service=backend --set "DEBUG=true"

# View variables
railway variables --kv
railway variables --json

# Use Railway variable references
railway variables --set 'DATABASE_URL=${{Postgres.DATABASE_URL}}'
railway variables --set 'REDIS_URL=${{Redis.REDIS_URL}}'
railway variables --set 'APP_URL=https://${{RAILWAY_PUBLIC_DOMAIN}}'
```

### Deployment

```bash
# Deploy current directory
railway up

# Deploy without waiting
railway up --detach

# View logs
railway logs
railway logs --tail 100

# Generate public domain
railway domain
```

### Local Development

```bash
# Run command with Railway environment
railway run npm start
railway run python manage.py migrate

# Run with specific service's variables
railway run --service=backend npm run dev
```

## Multi-Service Architecture

### Web + Worker Pattern

For applications with background task processing:

**Web Service:**

- Uses main Dockerfile with HTTP server
- Enable health checks (e.g., `/health`)
- Can use serverless if desired
- Config: `tools/deploy/railway/railway.app.json`

**Worker Service:**

- Uses worker Dockerfile with task runner
- **MUST disable serverless** (no HTTP wake mechanism)
- **MUST disable health checks** (no HTTP endpoint)
- Config: `tools/deploy/railway/railway.worker.json`
- Configure in dashboard: Settings → Deploy → Config file path

**Example Config Files:**

Web (`railway.app.json`):

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "tools/deploy/docker/Dockerfile.distroless"
  },
  "deploy": {
    "runtime": "V2",
    "sleepApplication": false,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300
  }
}
```

Worker (`railway.worker.json`):

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "tools/deploy/docker/Dockerfile.worker"
  },
  "deploy": {
    "runtime": "V2",
    "sleepApplication": false,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Example Dockerfiles:**

Web (Dockerfile):

```dockerfile
CMD ["python", "-m", "gunicorn", "app:create_app", "--bind", "0.0.0.0:8000"]
```

Worker (Dockerfile.worker):

```dockerfile
CMD ["python", "-m", "celery", "-A", "app.tasks", "worker"]
```

### Shared Configuration

Both services need access to:

- Database URL (`${{Postgres.DATABASE_URL}}`)
- Redis URL (`${{Redis.REDIS_URL}}`)
- Shared secrets (SECRET_KEY, API keys)

Copy shared variables to worker service:

```bash
railway service link "Web App"
SECRET=$(railway variables --kv | grep SECRET_KEY | cut -d'=' -f2-)

railway service link "Worker"
railway variables --set "SECRET_KEY=${SECRET}" \
    --set 'DATABASE_URL=${{Postgres.DATABASE_URL}}' \
    --set 'REDIS_URL=${{Redis.REDIS_URL}}' \
    --skip-deploys
```

## Troubleshooting

### Service Won't Wake Up

**Symptoms:** Service stuck in "Sleeping" state, requests timeout

**Causes:**

1. Serverless enabled on worker service (can't wake without HTTP)
2. Service crashed and didn't restart properly
3. Health check failing

**Solutions:**

1. Check if serverless is enabled: `railway.json` → `sleepApplication`
2. Disable serverless for workers in Railway dashboard
3. Check logs: `railway logs`
4. Redeploy: `railway up`

### Worker Not Processing Jobs

**Symptoms:** Jobs queued but not processed

**Causes:**

1. Worker sleeping due to serverless
2. Redis connection issue
3. Worker crashed

**Solutions:**

1. Disable serverless for worker service
2. Verify `REDIS_URL` is set correctly with `${{Redis.REDIS_URL}}`
3. Check worker logs: `railway service link "Worker" && railway logs`

### Build Failures

**Common issues:**

- Dockerfile not found: Check `dockerfilePath` in railway.json
- Dependencies not installing: Check build logs for errors
- Out of memory: Increase service resources in dashboard

### Health Check Failures

**For HTTP services:**

```json
{
  "deploy": {
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300
  }
}
```

**For workers:** Disable health checks in Railway dashboard (no HTTP endpoint)

## Best Practices

1. **Always disable serverless for workers** - They can't receive HTTP wake-up calls
2. **Use variable references** - `${{Postgres.DATABASE_URL}}` auto-updates if DB changes
3. **Set appropriate health checks** - Workers don't need them, web services do
4. **Use `--skip-deploys`** when setting multiple variables to avoid multiple redeploys
5. **Separate Dockerfiles** for web and worker services for clarity
6. **Configure per-service settings in dashboard** when railway.json can't distinguish services

## Railway Variables Reference

| Variable | Description |
|----------|-------------|
| `${{Postgres.DATABASE_URL}}` | PostgreSQL connection string |
| `${{Redis.REDIS_URL}}` | Redis connection string |
| `${{RAILWAY_PUBLIC_DOMAIN}}` | Auto-generated public domain |
| `${{RAILWAY_STATIC_URL}}` | URL for static assets |
| `${{PORT}}` | Railway's injected port (use for app port config) |

### Port Configuration

Railway injects `PORT` at runtime. **Never hardcode port numbers** - always reference dynamically:

```bash
# Correct - dynamic reference
railway variables --set 'LITESTAR_PORT=${{PORT}}'

# Wrong - hardcoded value won't update if Railway changes it
railway variables --set 'LITESTAR_PORT=8080'
```

## Resources

- [Railway Docs](https://docs.railway.com/)
- [Config-as-Code Reference](https://docs.railway.com/reference/config-as-code)
- [Serverless/App Sleeping](https://docs.railway.com/reference/app-sleeping)
- [Railway CLI](https://docs.railway.com/reference/cli-api)

## Official References

- <https://docs.railway.com/>
- <https://docs.railway.com/reference/app-sleeping>
- <https://docs.railway.com/cli/service>
- <https://docs.railway.com/cli/variable>
- <https://docs.railway.com/config-as-code/reference>
- <https://docs.railway.com/variables/reference>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Bash](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/bash.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
