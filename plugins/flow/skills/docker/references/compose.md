# Docker Compose Patterns

## Basic Service Definition

```yaml
# docker-compose.yml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: development  # Multi-stage target
    ports:
      - "8080:8080"
    environment:
      DATABASE_URL: postgresql://postgres:secret@db:5432/myapp
      REDIS_URL: redis://redis:6379
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./src:/app/src  # Dev hot-reload
    restart: unless-stopped

  db:
    image: postgres:16-bookworm
    environment:
      POSTGRES_PASSWORD: secret
      POSTGRES_DB: myapp
    ports:
      - "5432:5432"
    volumes:
      - pg-data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

volumes:
  pg-data:
  redis-data:
```

## Networks

```yaml
services:
  frontend:
    networks:
      - frontend-net

  api:
    networks:
      - frontend-net
      - backend-net

  db:
    networks:
      - backend-net

networks:
  frontend-net:
  backend-net:
    internal: true  # No external access
```

## Environment Variables

```yaml
services:
  api:
    # Inline
    environment:
      NODE_ENV: production
      LOG_LEVEL: info

    # From file
    env_file:
      - .env
      - .env.local

    # From host (passthrough)
    environment:
      - AWS_ACCESS_KEY_ID  # Uses host value
```

## Profiles (Conditional Services)

```yaml
services:
  api:
    build: .
    # Always starts (no profile)

  debug-tools:
    image: busybox
    profiles:
      - debug

  monitoring:
    image: grafana/grafana
    profiles:
      - monitoring
```

```bash
# Start with specific profiles
docker compose --profile debug --profile monitoring up
```

## Override Files

```yaml
# docker-compose.yml (base)
services:
  api:
    image: myapp:latest
    ports:
      - "8080:8080"

# docker-compose.override.yml (auto-loaded in dev)
services:
  api:
    build: .
    volumes:
      - ./src:/app/src
    environment:
      DEBUG: "true"

# docker-compose.prod.yml
services:
  api:
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
          cpus: "0.5"
```

```bash
# Dev (uses override automatically)
docker compose up

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Health Checks

```yaml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
```

## Secrets

```yaml
services:
  api:
    secrets:
      - db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

## Build Arguments

```yaml
services:
  api:
    build:
      context: .
      args:
        - BUILD_VERSION=1.2.3
        - PYTHON_VERSION=3.12
      cache_from:
        - myapp:cache
      platforms:
        - linux/amd64
        - linux/arm64
```

## Common Commands

```bash
# Start services
docker compose up -d

# Rebuild and start
docker compose up -d --build

# View logs
docker compose logs -f api

# Execute command in running service
docker compose exec api sh

# Run one-off command
docker compose run --rm api python manage.py migrate

# Stop and remove
docker compose down

# Stop, remove, and delete volumes
docker compose down -v
```
