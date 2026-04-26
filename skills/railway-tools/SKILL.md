---
name: railway-tools
description: "Use when deploying to Railway, editing railway.toml, railway.json, Procfile, configuring Railway services, databases, workers, environment variables, or troubleshooting Railway deployments."
---

# Railway Deployment (Flow Tools)

<workflow>

## 🚀 Official Railway Skills (Highly Recommended)

For full project management, deployment automation, and service orchestration, we highly recommend installing the official Railway agent skills:

- **use-railway**: Master skill for setting up projects, services, and handling deployments.

**Installation:**

```bash
npx skills add railwayapp/railway-skills
```

## Supplemental Patterns

The patterns below provide additional context for Flow-specific multi-service architectures and serverless constraints.

### Serverless / App Sleeping

Railway's serverless feature puts services to sleep after 10 minutes of no **outbound** traffic.

**When to disable serverless (`sleepApplication: false`):**

- Background workers (Celery, SAQ, RQ, Sidekiq)
- Queue processors
- Cron services
- Any service without an HTTP endpoint

### Multi-Service Architecture (Web + Worker)

For applications with background task processing, use distinct configuration files (e.g., `railway.app.json` and `railway.worker.json`) to manage different runtime requirements.

</workflow>

<guardrails>
## Guardrails

- **Disable Serverless for Workers:** Always set `sleepApplication: false` for background worker services.
- **Use Variable References:** Prefer `${{Service.VARIABLE}}` syntax (e.g., `${{Postgres.DATABASE_URL}}`) instead of hardcoding values.
- **Dynamic Port Binding:** Never hardcode the port. Always reference `${{PORT}}` for application port injection.
</guardrails>

<validation>
## Validation

- **Verify `sleepApplication: false` for Workers:** Ensure any background worker has `sleepApplication` explicitly set to `false`.
- **Check PORT Dynamic Reference:** Confirm that start commands and environment variables reference `${{PORT}}`.
</validation>

<example>
## Multi-Service Worker Example

**Configuration (`railway.worker.json`):**

```json
{
  "service": {
    "name": "worker",
    "sleepApplication": false
  },
  "deploy": {
    "startCommand": "python -m saq my_app.tasks.worker --workers 4"
  }
}
```

</example>
