# Litestar App Deployment Patterns

Production deployment patterns for Litestar ASGI applications, including server configuration, IAP authentication, and static asset serving.

## ASGI Server Configuration

### Entry Point

Litestar apps use the CLI for server startup:

```bash
# Standard startup (uvicorn backend)
app run --port 8080 --host 0.0.0.0

# Or using the Litestar CLI directly
litestar run --port 8080 --host 0.0.0.0
```

The `LITESTAR_APP` environment variable specifies the application factory or instance:

```bash
export LITESTAR_APP="myapp.asgi:create_app"
```

### Dockerfile CMD

```dockerfile
ENTRYPOINT ["tini", "--"]
CMD ["app", "server", "run", "--host", "0.0.0.0", "--port", "8080"]
```

### Server Backends

Litestar supports multiple ASGI servers:

| Server | Use Case | Notes |
|--------|----------|-------|
| **uvicorn** | General purpose, default | Well-tested, good ecosystem |
| **granian** | High-throughput, Rust-based | Lower latency, less memory |

## IAP (Identity-Aware Proxy) Authentication

Google Cloud IAP provides authentication at the infrastructure layer. Litestar can consume IAP JWT tokens for user identity.

### How It Works

1. Google Cloud IAP intercepts requests before they reach the application
2. IAP adds the `X-Goog-IAP-JWT-Assertion` header with a signed JWT
3. Litestar middleware verifies the JWT and extracts user identity
4. Users are auto-provisioned on first access (if enabled)

### Authentication Flow

```text
Client -> Cloud IAP -> Load Balancer -> Litestar App
                                          |
                                    X-Goog-IAP-JWT-Assertion header
                                          |
                                    IAPAuthenticationMiddleware
                                          |
                                    verify_iap_token()
                                          |
                                    resolve_iap_user()
                                          |
                                    (auto-provision if new)
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_IAP_ENABLED` | `false` | Enable IAP JWT authentication |
| `IAP_AUDIENCE` | `""` | Expected audience claim (required when IAP enabled) |
| `AUTH_IAP_AUTO_PROVISION` | `false` | Auto-create users from IAP token claims |
| `IAP_ALLOWED_DOMAINS` | `[]` | Email domain allowlist for auto-provisioned users |

### IAP Token Verification

The middleware verifies IAP JWTs using Google's public JWKS endpoint:

```python
IAP_AUTH_HEADER_KEY = "X-Goog-IAP-JWT-Assertion"
IAP_ISSUER = "https://cloud.google.com/iap"

async def verify_iap_token(raw_token: str, audience: str | Sequence[str]) -> IAPToken:
    """Verify IAP JWT using ES256 algorithm against Google JWKS."""
    jwks_client = await get_jwks_client()
    signing_key = await jwks_client.get_signing_key(raw_token)
    token_data = await async_(jwt.decode)(
        raw_token,
        key=signing_key.key,
        algorithms=["ES256"],
        audience=audience,
        issuer=IAP_ISSUER,
        options={"require": ["exp", "iat", "aud", "sub"]},
    )
    return IAPToken(sub=token_data["sub"], email=token_data.get("email"), ...)
```

### User Auto-Provisioning

When `AUTH_IAP_AUTO_PROVISION=true`, users are created automatically from IAP claims:

```python
async def resolve_iap_user(email: str, user_service: UserService) -> User | None:
    # Check domain allowlist
    email_domain = email.rsplit("@", maxsplit=1)[-1].lower()
    if email_domain not in allowed_domains:
        return None

    # Look up existing user
    user = await user_service.get_user_by_email(email)

    # Auto-provision if not found
    if user is None and settings.auth.IAP_AUTO_PROVISION_USERS:
        user = await user_service.create_user(
            UserCreate(email=email, name=email.split("@")[0], password=random_password, is_verified=True)
        )
    return user
```

### Dual Authentication (IAP + Local JWT)

The `IAPAuthenticationMiddleware` supports both IAP and local JWT authentication. IAP takes priority when the header is present, with fallback to Bearer token in the Authorization header:

```python
class IAPAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, connection):
        # 1. Try IAP authentication first (if enabled)
        if self.iap_enabled and self.iap_audience:
            iap_token = connection.headers.get("X-Goog-IAP-JWT-Assertion")
            if iap_token:
                token = await verify_iap_token(iap_token, self.iap_audience)
                user = await self.retrieve_iap_user_handler(token, connection)
                if user:
                    return AuthenticationResult(user=user, auth=token)

        # 2. Fall back to local JWT
        if self.local_auth_enabled:
            auth_header = connection.headers.get("Authorization")
            # ... standard Bearer token validation
```

## Static Asset Serving with Vite

### Build Integration

Frontend assets are built during the Docker image build and served by Litestar:

```dockerfile
# Install bun for JS bundling
COPY --from=oven/bun:latest /usr/local/bin/bun /usr/local/bin/bun

# Install JS dependencies
WORKDIR /app/src/js/web
RUN bun install --frozen-lockfile

# Build frontend assets
RUN uv run app manage assets build \
    && cd src/js/web && bun run build:all
```

### Email Templates

Email templates are built separately using bun:

```dockerfile
# Install email template dependencies
WORKDIR /app/src/js/templates
RUN bun install --frozen-lockfile

# Build email templates
RUN cd src/js/templates && bun run build:emails
```

The built templates are included in the Python wheel and served from the application's static directory.

## Deployment Checklist

- [ ] Set `LITESTAR_APP` environment variable to the application factory
- [ ] Configure `AUTH_IAP_ENABLED` and `IAP_AUDIENCE` if behind Cloud IAP
- [ ] Set `IAP_ALLOWED_DOMAINS` to restrict auto-provisioned user domains
- [ ] Build frontend assets (Vite) and email templates (bun) in Docker build
- [ ] Use `tini` as init system for proper signal handling
- [ ] Run as non-root user (UID 65532)
- [ ] Expose port 8080 (Cloud Run/GKE convention)
- [ ] Provide `/health` endpoint for readiness/liveness probes

## Official References

- <https://docs.litestar.dev/main/usage/cli.html>
- <https://cloud.google.com/iap/docs/identity-howto>
- <https://cloud.google.com/iap/docs/signed-headers-howto>
- <https://docs.litestar.dev/main/usage/middleware/index.html>
