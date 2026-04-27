# Docker Image Optimization

## Layer Caching

Order instructions from least to most frequently changing:

```dockerfile
# 1. Base image (rarely changes)
FROM python:3.12-slim-bookworm

# 2. System dependencies (changes occasionally)
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# 3. Application dependencies (changes when deps update)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Application code (changes most frequently)
COPY . .
```

## BuildKit Cache Mounts

Cache package manager downloads across builds:

```dockerfile
# syntax=docker/dockerfile:1

# pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# apt cache
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists \
    apt-get update && apt-get install -y libpq-dev

# Go modules cache
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    go build -o /app/server

# npm cache
RUN --mount=type=cache,target=/root/.npm \
    npm ci --omit=dev

# Cargo cache (Rust)
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/app/target \
    cargo build --release
```

## Secret Mounts

Use secrets during build without leaking them to the image:

```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm ci --omit=dev
```

```bash
docker build --secret id=npmrc,src=.npmrc .
```

## Minimal Base Images

| Base Image | Size | Use Case |
|-----------|------|----------|
| `scratch` | 0 MB | Static Go/Rust binaries |
| `gcr.io/distroless/static` | ~2 MB | Static binaries needing CA certs |
| `alpine:3.19` | ~7 MB | Minimal with shell + package manager |
| `debian:bookworm-slim` | ~80 MB | Need apt + glibc |
| `python:3.12-slim-bookworm` | ~150 MB | Python apps |
| `node:22-slim` | ~200 MB | Node.js apps |

## Reducing Image Size

### Combine RUN Commands

```dockerfile
# Bad: creates extra layers
RUN apt-get update
RUN apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*

# Good: single layer, cleanup in same step
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
```

### Remove Build Dependencies

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libffi-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y build-essential libffi-dev && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
```

### Python: Compile Bytecode & Strip

```dockerfile
FROM python:3.12-slim-bookworm AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
RUN python -m compileall /install/lib

FROM python:3.12-slim-bookworm
COPY --from=builder /install /usr/local
# .pyc files load faster, .py source can be removed if needed
```

### Go: Strip Binaries

```dockerfile
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /app/server
# -s: strip symbol table
# -w: strip DWARF debug info
# Further compress with UPX if needed:
# RUN upx --best /app/server
```

## Analyzing Image Size

```bash
# View layer sizes
docker history myapp:latest

# Use dive for interactive layer inspection
dive myapp:latest

# Compare image sizes
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}"
```

## .dockerignore Best Practices

Always include a `.dockerignore` to prevent large or sensitive files from entering the build context:

```text
.git
.github
.venv
node_modules
__pycache__
*.pyc
.env
.env.*
coverage
.pytest_cache
*.md
Dockerfile
docker-compose*.yml
```

## BuildKit Parallel Builds

```dockerfile
# Independent stages build in parallel
FROM node:22-slim AS frontend-builder
COPY frontend/ .
RUN npm ci && npm run build

FROM golang:1.22 AS backend-builder
COPY backend/ .
RUN go build -o /server

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=backend-builder /server /server
COPY --from=frontend-builder /dist /static
ENTRYPOINT ["/server"]
```

```bash
# Enable BuildKit (default in recent Docker)
DOCKER_BUILDKIT=1 docker build .
```
