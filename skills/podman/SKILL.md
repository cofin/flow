---
name: podman
description: "Auto-activate for podman commands, Containerfile. Podman expertise: rootless containers, pod management, systemd integration, and Docker CLI compatibility. Use when: running rootless containers, managing pods, using podman-compose, configuring systemd services, or working with OCI images without Docker daemon."
---

# Podman

## Overview

Podman is a daemonless, rootless container engine compatible with OCI images and the Docker CLI. It supports pod-level grouping, systemd integration via Quadlet, and secure secret management.

---

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Usage & Commands](references/usage.md)**
  - Core commands (run, build, exec, ps), rootless mode, pod creation, volume mounts, networking.
- **[Systemd Integration](references/systemd.md)**
  - Quadlet/systemd integration, auto-start containers, podman generate systemd.
- **[Secret Management](references/secrets.md)**
  - Secret management (podman secret create), secure credential handling.

---

## Official References

- <https://docs.podman.io/en/latest/>
- <https://podman.io/>
