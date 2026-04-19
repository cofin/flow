---
name: podman
description: "Auto-activate for podman commands, Containerfile. Podman expertise: rootless containers, pod management, systemd integration, and Docker CLI compatibility. Use when: running rootless containers, managing pods, using podman-compose, configuring systemd services, or working with OCI images without Docker daemon. Produces rootless container configurations, pod management, and systemd integration patterns. Not for Docker (see docker) or Kubernetes (see gke)."
---

# Podman

## Overview

Podman is a daemonless, rootless container engine compatible with OCI images and the Docker CLI. It supports pod-level grouping, systemd integration via Quadlet, and secure secret management.

---

<workflow>

## References Index

For detailed guides and code examples, refer to the following documents in `references/`:

- **[Usage & Commands](references/usage.md)**
  - Core commands (run, build, exec, ps), rootless mode, pod creation, volume mounts, networking.
- **[Systemd Integration](references/systemd.md)**
  - Quadlet/systemd integration, auto-start containers, podman generate systemd.
- **[Secret Management](references/secrets.md)**
  - Secret management (podman secret create), secure credential handling.

</workflow>

---

## Official References

- <https://docs.podman.io/en/latest/>
- <https://podman.io/>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Docker](https://github.com/cofin/flow/blob/main/templates/styleguides/tools/docker.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.

<guardrails>
## Guardrails

Add guardrails instructions here.
</guardrails>

<validation>
## Validation

Add validation instructions here.
</validation>

<example>
## Example

Add example instructions here.
</example>
