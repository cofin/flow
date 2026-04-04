# Dockerfile Patterns

## Multi-Stage Build

```dockerfile
# Stage 1: Build
FROM golang:1.22-bookworm AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=${TARGETARCH} go build -ldflags="-s -w" -o /app/server ./cmd/server

# Stage 2: Runtime (distroless)
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /app/server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
```

## Multi-Architecture Builds

```dockerfile
# TARGETARCH is automatically set by BuildKit
ARG TARGETARCH

FROM --platform=$BUILDPLATFORM golang:1.22 AS builder
ARG TARGETARCH
RUN GOARCH=${TARGETARCH} go build -o /app/server

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /app/server /server
ENTRYPOINT ["/server"]
```

```bash
# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 -t myapp:latest --push .
```

## Distroless Base Images

Choose the right distroless image:

| Image | Use Case |
|-------|----------|
| `gcr.io/distroless/static-debian12` | Statically compiled (Go, Rust) |
| `gcr.io/distroless/cc-debian12` | C/C++ with dynamically linked libs |
| `gcr.io/distroless/base-debian12` | Needs glibc + libssl + openssl |
| `gcr.io/distroless/python3-debian12` | Python applications |
| `gcr.io/distroless/java21-debian12` | Java applications |

Always use the `:nonroot` tag variant for non-root execution.

## Python Multi-Stage with uv Cache Mount

Use `--mount=type=cache` to persist uv's download cache across builds. This avoids re-downloading packages on every build when only source code changes.

```dockerfile
FROM python:3.12-slim-bookworm AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable
COPY src/ ./src/

FROM gcr.io/distroless/python3-debian12:nonroot
WORKDIR /app
COPY --from=builder /app/.venv/lib/python3.12/site-packages /usr/lib/python3.12/site-packages
COPY --from=builder /app/src ./src
ENTRYPOINT ["python", "-m", "myapp"]
```

## Node.js Multi-Stage

```dockerfile
FROM node:22-bookworm-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev
COPY . .
RUN npm run build

FROM gcr.io/distroless/nodejs22-debian12:nonroot
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["dist/server.js"]
```

## Non-Root User

UID 65532 is the `nonroot` user in distroless images. Align custom user IDs with this value for consistency across distroless and non-distroless images.

```dockerfile
# For non-distroless images — use UID 65532 to match distroless nonroot
FROM python:3.12-slim-bookworm
RUN groupadd --gid 65532 nonroot \
 && useradd --uid 65532 --gid 65532 --no-create-home --shell /bin/false nonroot
USER nonroot
WORKDIR /app
COPY --chown=nonroot:nonroot src/ ./src/
```

## Tini Init System

Use tini to properly handle signals and reap zombie processes:

```dockerfile
FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends tini && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["tini", "--"]
CMD ["python", "-m", "myapp"]
```

## .dockerignore

```text
# .dockerignore
.git
.github
.venv
__pycache__
*.pyc
node_modules
.env
.env.*
*.md
!README.md
Dockerfile
docker-compose*.yml
.dockerignore
coverage
.pytest_cache
.mypy_cache
dist
build
```

## Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["/app/healthcheck"]

# Or with curl (adds curl to image)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
```

## Labels & Metadata

```dockerfile
LABEL org.opencontainers.image.source="https://github.com/org/repo"
LABEL org.opencontainers.image.description="My application"
LABEL org.opencontainers.image.version="1.0.0"
```
