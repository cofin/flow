---
name: docker
description: "Use when editing Dockerfile, Containerfile-like Docker syntax, docker-compose.yml, docker-compose.yaml, .dockerignore, multi-stage builds, BuildKit cache mounts, Compose services, or image optimization."
---

# Docker

## Overview

Docker provides OS-level virtualization via containers. This skill covers Dockerfile best practices, multi-stage builds, distroless images, Compose orchestration, and BuildKit optimizations.

---

## Multi-Stage Build Quick Reference

Multi-stage builds separate build-time dependencies from the runtime image, producing minimal production images.

```dockerfile
# ---- Stage 1: dependency builder ----
FROM python:3.12-slim-bookworm AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
# Cache uv's package download cache across builds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ---- Stage 2: runtime (distroless, non-root) ----
FROM gcr.io/distroless/python3-debian12:nonroot
WORKDIR /app
COPY --from=builder /app/.venv/lib/python3.12/site-packages /usr/lib/python3.12/site-packages
COPY src/ ./src/
ENTRYPOINT ["python", "-m", "myapp"]
```

Key rules:

- Name every stage (`AS builder`, `AS runner`, etc.).
- Only the final stage ends up in the shipped image.
- Copy only what is needed from earlier stages with `COPY --from=`.

---

## Compose Quick Reference

```yaml
# compose.yml
services:
  app:
    build: .
    image: myapp:dev
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://app:secret@db:5432/mydb
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: mydb
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d mydb"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pg_data:
```

```bash
# Common Compose commands
docker compose up -d          # start detached
docker compose logs -f app    # follow service logs
docker compose exec app bash  # shell into running container
docker compose down -v        # stop and remove volumes
docker compose build --no-cache  # full rebuild
```

---

## BuildKit Cache Mounts

`--mount=type=cache` persists a directory between builds so package managers do not re-download.

```dockerfile
# uv (Python)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# pip
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# apt
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends curl

# npm
RUN --mount=type=cache,target=/root/.npm \
    npm ci --omit=dev

# Go modules
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download
```

Enable BuildKit (default in Docker 23+):

```bash
export DOCKER_BUILDKIT=1
docker build .
# or
docker buildx build .
```

---

## Production Patterns

### uv Package Manager

`uv` is a fast Python package/project manager. Use it as the build-stage installer, then copy the resulting `.venv` into the runtime stage.

```dockerfile
FROM python:3.12-slim-bookworm AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable
```

### Distroless Base Images

| Image | Use case |
|-------|----------|
| `gcr.io/distroless/static-debian12:nonroot` | Statically compiled binaries (Go, Rust) |
| `gcr.io/distroless/base-debian12:nonroot` | Dynamically linked, needs glibc |
| `gcr.io/distroless/python3-debian12:nonroot` | Python applications |
| `gcr.io/distroless/nodejs22-debian12:nonroot` | Node.js applications |

Always use the `:nonroot` tag — the image user is UID 65532.

### tini Init

`tini` properly forwards signals and reaps zombie processes. Use it when the base image does not include an init system (e.g., non-distroless slim images).

```dockerfile
FROM python:3.12-slim-bookworm
RUN apt-get update \
 && apt-get install -y --no-install-recommends tini \
 && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "myapp"]
```

Distroless images already run as non-root; for non-distroless images add tini + explicit non-root user.

### Non-Root User (UID 65532)

UID 65532 is the `nonroot` user in distroless images. Align custom user IDs with this value for consistency.

```dockerfile
# For non-distroless images
RUN groupadd --gid 65532 nonroot \
 && useradd --uid 65532 --gid 65532 --no-create-home --shell /bin/false nonroot
USER nonroot
```

### .dockerignore

```text
.git
.github
.venv
__pycache__
*.pyc
*.pyo
node_modules
.env
.env.*
Dockerfile
docker-compose*.yml
compose*.yml
.dockerignore
coverage
.pytest_cache
.mypy_cache
.ruff_cache
dist
build
*.md
!README.md
```

<workflow>

## Workflow

1. **Write Dockerfile** — multi-stage, pin base tags, use cache mounts.
2. **Write .dockerignore** — exclude `.git`, `.env`, `node_modules`, `__pycache__`.
3. **Build locally** — `docker buildx build -t myimage:dev .`
4. **Inspect** — `docker image inspect myimage:dev` for size; `dive myimage:dev` for layer breakdown.
5. **Run as non-root check** — `docker run --rm myimage:dev id` should print `uid=65532`.
6. **Compose integration** — use `compose.yml` with health checks and `depends_on` conditions.

</workflow>

<guardrails>

## Guardrails

- **Always multi-stage** — never ship build tools, compilers, or dev dependencies in the final image.
- **Always non-root** — use `:nonroot` distroless tags or add an explicit non-root user (UID 65532). Never run as root in production.
- **Always .dockerignore** — prevents leaking `.env`, secrets, `.git`, and large directories into the build context.
- **Pin base image tags** — use full tags (`python:3.12-slim-bookworm`, not `python:latest`) to ensure reproducible builds.
- **Use BuildKit cache mounts** for all package managers to keep CI builds fast.
- **No secrets in layers** — never `COPY .env` or `RUN echo SECRET=...`. Use `--secret` mount or runtime injection.

</guardrails>

<validation>

## Validation Checkpoint

Before delivering Dockerfile or Compose config, verify:

- [ ] Multi-stage build separates builder from runtime stage
- [ ] Base image tags are pinned (no `:latest`)
- [ ] `.dockerignore` is present and excludes secrets/caches
- [ ] Final image runs as non-root (UID 65532 or equivalent)
- [ ] No secrets baked into layers
- [ ] Cache mounts used for package manager steps
- [ ] Health check defined in Compose or Dockerfile for long-running services

</validation>

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Dockerfile Patterns](references/dockerfile.md)**
  - Multi-stage builds, distroless images, TARGETARCH for multi-arch, non-root users, tini init, .dockerignore, uv cache mounts.
- **[Compose](references/compose.md)**
  - docker-compose.yml patterns, service dependencies, volumes, networks, health checks.
- **[Optimization](references/optimization.md)**
  - Layer caching, BuildKit cache mounts, minimal base images, bytecode compilation, reducing image size.

---

<example>

## Example: Multi-Stage Python Dockerfile

```dockerfile
# Build stage
FROM python:3.12-slim-bookworm AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Runtime stage
FROM gcr.io/distroless/python3-debian12:nonroot
WORKDIR /app
COPY --from=builder /app/.venv/lib/python3.12/site-packages /usr/lib/python3.12/site-packages
COPY src/ ./src/
ENTRYPOINT ["python", "-m", "myapp"]
```

</example>

---

## Official References

- <https://docs.docker.com/>
- <https://github.com/GoogleContainerTools/distroless>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Docker](https://github.com/cofin/flow/blob/main/templates/styleguides/tools/docker.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
