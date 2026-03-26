# Podman Usage & Commands

## Core Commands

```bash
# Run a container (Docker-compatible syntax)
podman run -d --name myapp -p 8080:8080 myimage:latest

# Build an image
podman build -t myapp:latest .

# List running containers
podman ps

# List all containers (including stopped)
podman ps -a

# Execute command in running container
podman exec -it myapp /bin/sh

# View logs
podman logs -f myapp

# Stop and remove
podman stop myapp
podman rm myapp

# Remove all stopped containers
podman container prune
```

## Rootless Mode

Podman runs rootless by default for the current user. No daemon required.

```bash
# Check rootless mode
podman info --format '{{.Host.Security.Rootless}}'

# Rootless containers use user namespaces
# UID mapping is configured in /etc/subuid and /etc/subgid
cat /etc/subuid
# username:100000:65536

# Run as specific user inside container
podman run --user 1001:1001 myimage

# Use --userns=keep-id to map host UID to container UID
podman run --userns=keep-id -v ./data:/data myimage
```

## Pod Management

Pods group containers that share network and IPC namespaces (like Kubernetes pods).

```bash
# Create a pod
podman pod create --name myapp-pod -p 8080:8080 -p 5432:5432

# Add containers to the pod
podman run -d --pod myapp-pod --name api myapi:latest
podman run -d --pod myapp-pod --name db postgres:16

# Containers in the same pod communicate via localhost
# API connects to DB at localhost:5432

# List pods
podman pod ls

# Stop/start all containers in a pod
podman pod stop myapp-pod
podman pod start myapp-pod

# Remove pod and all its containers
podman pod rm -f myapp-pod
```

## Volume Mounts

```bash
# Named volume
podman volume create mydata
podman run -v mydata:/data myimage

# Bind mount (use :Z for SELinux relabeling)
podman run -v ./local-dir:/container-dir:Z myimage

# Read-only mount
podman run -v ./config:/etc/myapp/config:ro,Z myimage

# tmpfs mount
podman run --tmpfs /tmp:size=100m myimage
```

## Networking

```bash
# Create a network
podman network create mynet

# Run containers on the network
podman run -d --network mynet --name api myapi:latest
podman run -d --network mynet --name db postgres:16

# Containers resolve each other by name
# api can connect to db:5432

# Inspect network
podman network inspect mynet

# Connect existing container to network
podman network connect mynet existing-container
```

## Image Management

```bash
# Pull image
podman pull docker.io/library/postgres:16

# List images
podman images

# Tag image
podman tag myapp:latest registry.example.com/myapp:v1.0

# Push to registry
podman push registry.example.com/myapp:v1.0

# Remove unused images
podman image prune -a

# Export/import images
podman save -o myapp.tar myapp:latest
podman load -i myapp.tar
```

## Podman Compose

```bash
# Install podman-compose
pip install podman-compose

# Use existing docker-compose.yml
podman-compose up -d
podman-compose down
podman-compose logs -f

# Or use Docker Compose directly with Podman socket
systemctl --user enable --now podman.socket
export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/podman/podman.sock
docker compose up -d  # Uses Podman backend
```

## Generating Kubernetes YAML

```bash
# Generate Kubernetes YAML from a pod
podman generate kube myapp-pod > myapp.yaml

# Play (deploy) Kubernetes YAML
podman kube play myapp.yaml

# Tear down
podman kube down myapp.yaml
```

## Useful Flags

```bash
# Auto-remove container on exit
podman run --rm myimage

# Resource limits
podman run --memory=512m --cpus=2 myimage

# Environment variables
podman run -e KEY=value --env-file=.env myimage

# Restart policy
podman run --restart=on-failure:3 myimage

# Init process (reap zombies)
podman run --init myimage
```
