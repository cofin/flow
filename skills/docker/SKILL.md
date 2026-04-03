---
name: docker
description: "Auto-activate for Dockerfile, docker-compose.yml, docker-compose.yaml, .dockerignore. Docker expertise: multi-stage builds, distroless images, Compose, BuildKit, and container optimization. Use when: writing Dockerfiles, optimizing image size, configuring docker-compose, using BuildKit features, or deploying containerized applications. Produces optimized Dockerfiles with multi-stage builds, Compose configurations, and BuildKit patterns. Not for Podman (see podman) or container orchestration (see gke/cloud-run)."
---

# Docker

## Overview

Docker provides OS-level virtualization via containers. This skill covers Dockerfile best practices, multi-stage builds, distroless images, Compose orchestration, and BuildKit optimizations.

---

<workflow>

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Dockerfile Patterns](references/dockerfile.md)**
  - Multi-stage builds, distroless images, TARGETARCH for multi-arch, non-root users, tini init, .dockerignore.
- **[Compose](references/compose.md)**
  - docker-compose.yml patterns, service dependencies, volumes, networks, health checks.
- **[Optimization](references/optimization.md)**
  - Layer caching, BuildKit cache mounts, minimal base images, bytecode compilation, reducing image size.

</workflow>

<example>

## Example: Multi-Stage Dockerfile

```dockerfile
# Build stage
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

# Runtime stage
FROM gcr.io/distroless/python3-debian12
COPY --from=builder /app/.venv /app/.venv
COPY src/ /app/src/
ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app
CMD ["python", "-m", "app"]
```

</example>

---

## Official References

- <https://docs.docker.com/>
- <https://github.com/GoogleContainerTools/distroless>
