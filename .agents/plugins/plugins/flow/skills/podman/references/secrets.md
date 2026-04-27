# Podman Secret Management

## Creating Secrets

```bash
# From a file
echo -n "my-database-password" | podman secret create db_password -

# From a file path
podman secret create tls_cert ./server.crt

# From environment variable
printf '%s' "${DB_PASSWORD}" | podman secret create db_password -
```

## Listing & Inspecting Secrets

```bash
# List all secrets
podman secret ls

# Inspect secret metadata (does not show the value)
podman secret inspect db_password

# Remove a secret
podman secret rm db_password
```

## Using Secrets in Containers

```bash
# Mount secret as a file (default: /run/secrets/<name>)
podman run -d \
    --secret db_password \
    --name myapp \
    myimage:latest

# Inside the container, read: cat /run/secrets/db_password

# Mount at a custom path
podman run -d \
    --secret db_password,target=/etc/myapp/db-pass \
    myimage:latest

# Expose as environment variable
podman run -d \
    --secret db_password,type=env,target=DATABASE_PASSWORD \
    myimage:latest
```

## Secrets in Quadlet

```ini
# ~/.config/containers/systemd/myapp.container
[Container]
Image=myimage:latest
Secret=db_password,type=mount,target=/run/secrets/db_password
Secret=api_key,type=env,target=API_KEY
```

## Secrets in Podman Compose

```yaml
# docker-compose.yml (podman-compose compatible)
services:
  api:
    image: myapi:latest
    secrets:
      - db_password
      - api_key

secrets:
  db_password:
    external: true  # Must be created with `podman secret create` first
  api_key:
    file: ./secrets/api_key.txt  # Created from file
```

## Application Pattern: Reading Secrets

```python
# Python example: read secret from file
import os
from pathlib import Path

def get_secret(name: str) -> str:
    """Read a secret from /run/secrets/ or fall back to env var."""
    secret_path = Path(f"/run/secrets/{name}")
    if secret_path.exists():
        return secret_path.read_text().strip()
    value = os.environ.get(name.upper())
    if value is None:
        raise ValueError(f"Secret '{name}' not found in /run/secrets/ or environment")
    return value

db_password = get_secret("db_password")
```

```go
// Go example: read secret from file
func getSecret(name string) (string, error) {
    path := filepath.Join("/run/secrets", name)
    data, err := os.ReadFile(path)
    if err != nil {
        // Fall back to environment variable
        if val, ok := os.LookupEnv(strings.ToUpper(name)); ok {
            return val, nil
        }
        return "", fmt.Errorf("secret %q not found", name)
    }
    return strings.TrimSpace(string(data)), nil
}
```

## Security Best Practices

1. **Never bake secrets into images** -- use runtime secret injection.
2. **Prefer file-based secrets over environment variables** -- env vars appear in `podman inspect` and process listings.
3. **Use `printf '%s'` instead of `echo`** -- avoids newline issues and shell history with some shells.
4. **Rotate secrets** by creating a new secret and restarting the container:

```bash
echo -n "new-password" | podman secret create db_password_v2 -
podman stop myapp
podman rm myapp
podman run -d --secret db_password_v2,target=/run/secrets/db_password --name myapp myimage
podman secret rm db_password  # Remove old secret
```
