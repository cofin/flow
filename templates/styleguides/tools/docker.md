# Docker Style Guide

## Build Patterns

### Multi-Stage Builds

Always use multi-stage builds to minimize image size:

```dockerfile
# Stage 1: Build
FROM python:3.13-slim-bookworm AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

# Stage 2: Runtime
FROM gcr.io/distroless/cc-debian12:nonroot AS runner
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
ENTRYPOINT ["/app/.venv/bin/python", "-m", "app"]
```

### Base Image Selection

| Use Case | Base Image |
|----------|-----------|
| Production (minimal) | `gcr.io/distroless/cc-debian12:nonroot` |
| Production (needs shell) | `python:3.13-slim-bookworm` |
| Build stage | `python:3.13-slim-bookworm` |
| Multi-arch aware | Use `--platform=$BUILDPLATFORM` |

### Security

- **Always run as non-root**: Use `USER nonroot` or distroless `:nonroot` tag
- **Use tini for signal handling** in non-distroless images: `ENTRYPOINT ["tini", "--"]`
- **Never store secrets in images**: Use build args or runtime env vars
- **Pin base image digests** for reproducibility in CI

### Dependency Installation with uv

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable
```

### Multi-Architecture Support

```dockerfile
# Copy arch-specific shared libraries
RUN ARCH=$(uname -m) && \
    cp /usr/lib/${ARCH}-linux-gnu/libz.so.1 /runtime/lib/ && \
    cp /usr/lib/${ARCH}-linux-gnu/libffi.so.8 /runtime/lib/
```

## Compose Patterns

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

## Anti-Patterns

- **Don't use `latest` tag** in production — pin versions
- **Don't `COPY . .` early** — copy dependency files first for layer caching
- **Don't install dev dependencies** in production images
- **Don't run as root** — always specify a non-root user
- **Don't use `ADD` for local files** — use `COPY` (ADD has implicit tar extraction)
