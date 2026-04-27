# Dockerfile Patterns for Cloud Run

Production-ready Dockerfile patterns for Python applications on Cloud Run, using multi-stage builds with uv package manager.

## Standard Multi-Stage Build (python-base / builder / runner)

Three-stage pattern using `python:3.13-slim-bookworm` as the base image.

### Stage 1: python-base

Install system dependencies and uv package manager:

```dockerfile
ARG BUILDER_IMAGE=python:3.13-slim-bookworm

FROM ${BUILDER_IMAGE} AS python-base
RUN apt-get update \
  && apt-get upgrade -y \
  && apt-get install -y --no-install-recommends build-essential git tini curl \
  && apt-get autoremove -y \
  && apt-get clean -y \
  && rm -rf /root/.cache /var/apt/lists/* /var/cache/apt/* \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && mkdir -p /workspace/app

# Install uv from official container image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
```

### Stage 2: builder

Install dependencies and build the application wheel:

```dockerfile
FROM python-base AS builder
ARG UV_INSTALL_ARGS="--no-dev"

ENV GRPC_PYTHON_BUILD_WITH_CYTHON=1 \
  UV_LINK_MODE=copy \
  UV_NO_CACHE=1 \
  UV_COMPILE_BYTECODE=1 \
  UV_SYSTEM_PYTHON=1 \
  PATH="/workspace/app/.venv/bin:/usr/local/bin:$PATH" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONFAULTHANDLER=1 \
  PYTHONHASHSEED=random \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8

WORKDIR /workspace/app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies without the project itself
RUN uv sync ${UV_INSTALL_ARGS} --frozen --no-install-project --no-editable \
  && uv export ${UV_INSTALL_ARGS} --frozen --no-hashes --output-file=requirements.txt

# Copy application source and build
COPY src ./src
RUN uv sync ${UV_INSTALL_ARGS} --frozen --no-editable \
  && uv build
```

### Stage 3: runner

Minimal runtime image with non-root user:

```dockerfile
FROM python-base AS runner
ARG UV_INSTALL_ARGS="--no-dev"
ARG LITESTAR_APP="myapp.asgi:app"

ENV PATH="/workspace/app/.venv/bin:/usr/local/bin:$PATH" \
  UV_LINK_MODE=copy \
  UV_NO_CACHE=1 \
  UV_COMPILE_BYTECODE=1 \
  UV_SYSTEM_PYTHON=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONFAULTHANDLER=1 \
  PYTHONHASHSEED=random \
  LANG=C.UTF-8 \
  LC_ALL=C.UTF-8 \
  HOME="/workspace/app" \
  LITESTAR_APP="${LITESTAR_APP}"

# Non-root user with UID 65532
RUN addgroup --system --gid 65532 nonroot \
  && adduser --no-create-home --system --uid 65532 nonroot \
  && chown -R nonroot:nonroot /workspace

COPY --from=builder --chown=65532:65532 /workspace/app/dist /tmp/
WORKDIR /workspace/app

RUN uv pip install --quiet --disable-pip-version-check /tmp/*.whl \
  && rm -Rf /tmp/* \
  && chown -R nonroot:nonroot /workspace/app

USER nonroot
STOPSIGNAL SIGINT
EXPOSE 8080

# tini as init system for proper signal handling
ENTRYPOINT ["tini", "--"]
CMD ["app", "run", "--port", "8080", "--host", "0.0.0.0"]
VOLUME /workspace/app
```

## Distroless Variant (4-Stage Build)

Uses `gcr.io/distroless/cc-debian12:nonroot` for maximum security -- no shell, no package manager in the runtime image.

### Stage Layout

```text
python-base  ->  builder  ->  runtime-prep  ->  runner  (->  worker)
```

### Build Arguments and Base Images

```dockerfile
# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.13
ARG DEBIAN_VERSION=bookworm
ARG BUILDER_IMAGE=python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION}
ARG RUN_IMAGE=gcr.io/distroless/cc-debian12:nonroot
```

### Stage 3: runtime-prep (Unique to Distroless)

Prepares Python interpreter and shared libraries for the distroless base, which has no Python runtime:

```dockerfile
FROM python-base AS runtime-prep

# TARGETARCH provided by Docker buildx for multi-arch support
ARG TARGETARCH

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# Create non-root user matching distroless nonroot user
RUN groupadd --system --gid 65532 nonroot \
    && useradd --no-create-home --system --uid 65532 --gid 65532 nonroot \
    && mkdir -p /app \
    && chown -R nonroot:nonroot /app

# Create venv with COPIED Python (not symlinked) for distroless
RUN python -m venv --copies /app/.venv

# Install dependencies into the venv
COPY --from=builder --chown=65532:65532 /app/requirements.txt /tmp/requirements.txt
COPY --from=builder --chown=65532:65532 /app/dist/*.whl /tmp/

RUN uv pip install --quiet --no-cache-dir --no-deps \
        --requirement=/tmp/requirements.txt \
    && uv pip install --quiet --no-cache-dir --no-deps /tmp/*.whl \
    && rm -rf /tmp/*

# Multi-arch library copying
RUN ARCH_DIR=$([ "$TARGETARCH" = "arm64" ] && echo "aarch64-linux-gnu" || echo "x86_64-linux-gnu") \
    && mkdir -p /runtime-libs/lib /runtime-libs/usr/lib \
    && cp -a /lib/${ARCH_DIR} /runtime-libs/lib/ \
    && cp -a /usr/lib/${ARCH_DIR} /runtime-libs/usr/lib/
```

### Stage 4: Distroless Runner

```dockerfile
FROM ${RUN_IMAGE} AS runner

ARG LITESTAR_APP="myapp.asgi:create_app"

ENV PATH="/app/.venv/bin:/usr/local/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    LITESTAR_APP="${LITESTAR_APP}"

# Copy Python interpreter and standard library from runtime-prep
COPY --from=runtime-prep /usr/local/lib/ /usr/local/lib/
COPY --from=runtime-prep /usr/local/bin/python /usr/local/bin/python
COPY --from=runtime-prep /etc/ld.so.cache /etc/ld.so.cache

# Copy tini for proper signal handling
COPY --from=runtime-prep /usr/bin/tini /usr/local/bin/tini

# Copy required shared libraries (architecture-aware)
COPY --from=runtime-prep /runtime-libs/lib/ /lib/
COPY --from=runtime-prep /runtime-libs/usr/lib/ /usr/lib/
COPY --from=runtime-prep /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Copy the application virtual environment
WORKDIR /app
COPY --from=runtime-prep --chown=65532:65532 /app/.venv /app/.venv

STOPSIGNAL SIGTERM
USER nonroot
EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/tini", "--"]
CMD ["app", "server", "run", "--host", "0.0.0.0", "--port", "8080"]
```

### Stage 5: Worker Target (Cloud Run Jobs)

Extends the runner for batch/background processing:

```dockerfile
FROM runner AS worker

EXPOSE 8080
HEALTHCHECK NONE
CMD ["app-worker"]
```

## Key Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `PYTHONUNBUFFERED` | `1` | Disable output buffering for real-time logging |
| `PYTHONFAULTHANDLER` | `1` | Enable faulthandler for debugging crashes |
| `UV_COMPILE_BYTECODE` | `1` | Pre-compile .pyc files for faster startup |
| `UV_NO_CACHE` | `1` | Skip cache to reduce image size |
| `UV_LINK_MODE` | `copy` | Copy files instead of hardlinking (required for multi-stage) |
| `UV_SYSTEM_PYTHON` | `1` | Use system Python instead of managed versions |
| `PYTHONDONTWRITEBYTECODE` | `1` | Prevent runtime .pyc generation (already compiled) |
| `PYTHONHASHSEED` | `random` | Randomize hash seed for security |

## Key Patterns

- **Non-root user**: Always run as UID 65532 (`nonroot`) for security
- **tini init system**: Use `tini` as PID 1 for proper signal forwarding and zombie reaping
- **Layer caching**: Copy `pyproject.toml` and `uv.lock` before source code
- **Wheel install**: Build a wheel in the builder stage, install only the wheel in the runner
- **Multi-arch**: Use `TARGETARCH` build arg with Docker buildx for amd64/arm64 support
- **Distroless**: Use `python -m venv --copies` (not symlinks) since distroless has no system Python
- **Bun for JS builds**: Install `COPY --from=oven/bun:latest /usr/local/bin/bun /usr/local/bin/bun` for frontend asset builds

## Official References

- <https://cloud.google.com/run/docs/deploying>
- <https://github.com/GoogleContainerTools/distroless>
- <https://docs.astral.sh/uv/guides/integration/docker/>
- <https://github.com/krallin/tini>
