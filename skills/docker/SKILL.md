---
name: docker
description: "Auto-activate for Dockerfile, docker-compose.yml, docker-compose.yaml, .dockerignore. Docker expertise: multi-stage builds, distroless images, Compose, BuildKit, and container optimization. Use when: writing Dockerfiles, optimizing image size, configuring docker-compose, using BuildKit features, or deploying containerized applications."
---

# Docker

## Overview

Docker provides OS-level virtualization via containers. This skill covers Dockerfile best practices, multi-stage builds, distroless images, Compose orchestration, and BuildKit optimizations.

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Dockerfile Patterns](references/dockerfile.md)**
  - Multi-stage builds, distroless images, TARGETARCH for multi-arch, non-root users, tini init, .dockerignore.
- **[Compose](references/compose.md)**
  - docker-compose.yml patterns, service dependencies, volumes, networks, health checks.
- **[Optimization](references/optimization.md)**
  - Layer caching, BuildKit cache mounts, minimal base images, bytecode compilation, reducing image size.

---

## Official References

- <https://docs.docker.com/>
- <https://github.com/GoogleContainerTools/distroless>
