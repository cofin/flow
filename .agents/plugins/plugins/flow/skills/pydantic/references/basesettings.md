# BaseSettings Deep Reference

`BaseSettings` (from `pydantic-settings`) extends `BaseModel` with automatic population from environment variables, `.env` files, secrets directories, and custom sources.

## Installation

```bash
pip install pydantic-settings
```

## SettingsConfigDict Options

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        # --- .env file loading ---
        env_file=".env",                  # path or tuple of paths (evaluated in order)
        env_file_encoding="utf-8",

        # --- Nested model delimiter ---
        env_nested_delimiter="__",        # DATABASE__HOST → database.host

        # --- Key matching ---
        case_sensitive=False,             # default: False (env vars are case-insensitive)
        env_prefix="APP_",                # APP_DEBUG=true → debug=True

        # --- Secrets ---
        secrets_dir="/run/secrets",       # Docker/K8s secrets volume path

        # --- Extra fields ---
        extra="ignore",                   # "allow", "ignore", or "forbid"

        # --- Validation ---
        validate_default=True,            # validate default values too
    )
```

## Priority Chain

Values are resolved in this order (highest to lowest priority):

1. **Explicit constructor arguments**: `AppSettings(debug=True)`
2. **Environment variables**: `export APP_DEBUG=true`
3. **`.env` file(s)**: `.env` or specified paths
4. **Secrets directory**: files named after the field
5. **Field defaults**: `debug: bool = False`

## Nested Models with `__` Delimiter

```python
from pydantic import BaseModel, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    name: str = "app"
    user: str = "postgres"
    password: SecretStr = SecretStr("postgres")

    @computed_field
    @property
    def url(self) -> str:
        pwd = self.password.get_secret_value()
        return f"postgresql+asyncpg://{self.user}:{pwd}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: SecretStr | None = None

    @computed_field
    @property
    def url(self) -> str:
        auth = f":{self.password.get_secret_value()}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
    )

    debug: bool = False
    secret_key: SecretStr
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
```

With `env_nested_delimiter="__"`, the following env vars map to the nested models:

```bash
DATABASE__HOST=db.prod.internal
DATABASE__PORT=5433
DATABASE__NAME=myapp
DATABASE__USER=appuser
DATABASE__PASSWORD=s3cret

REDIS__HOST=redis.prod.internal
REDIS__PASSWORD=redispass

SECRET_KEY=my-super-secret-key
DEBUG=false
```

## Secrets Directory Pattern

For Docker and Kubernetes, secrets are often mounted as files. BaseSettings reads them automatically if you set `secrets_dir`.

```python
class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        secrets_dir="/run/secrets",
    )

    secret_key: SecretStr       # reads /run/secrets/secret_key
    database_password: SecretStr  # reads /run/secrets/database_password
```

File content is read as the field value. For `SecretStr`, the value is wrapped automatically.

You can also pass the secrets directory at runtime:

```python
settings = AppSettings(_secrets_dir="/custom/secrets/path")
```

## Multiple `.env` Files

Pass a tuple of paths. Later files take lower priority (first match wins):

```python
class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local", ".env.production"),
        env_file_encoding="utf-8",
    )
```

You can also override the env file at instantiation:

```python
settings = AppSettings(_env_file=".env.test")
```

## Custom Settings Sources

Implement `PydanticBaseSettingsSource` to add custom backends (e.g., AWS SSM, Vault, remote config):

```python
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


class VaultSettingsSource(PydanticBaseSettingsSource):
    """Load settings from HashiCorp Vault."""

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[object, str, bool]:
        # fetch from Vault here
        value = fetch_from_vault(field_name)
        return value, field_name, False

    def __call__(self) -> dict[str, object]:
        return {
            field_name: self.get_field_value(field_info, field_name)[0]
            for field_name, field_info in self.settings_cls.model_fields.items()
        }


class AppSettings(BaseSettings):
    secret_key: str
    db_password: str

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            VaultSettingsSource(settings_cls),  # custom source in priority chain
            dotenv_settings,
            file_secret_settings,
        )
```

## Full Working Example

A complete settings setup for a web application with database, redis, and app-level config:

```python
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseModel):
    host: str = "localhost"
    port: int = 5432
    name: str = "app"
    user: str = "postgres"
    password: SecretStr = SecretStr("postgres")
    pool_size: int = Field(default=5, ge=1, le=100)
    max_overflow: int = Field(default=10, ge=0, le=50)

    @computed_field
    @property
    def url(self) -> str:
        pwd = self.password.get_secret_value()
        return f"postgresql+asyncpg://{self.user}:{pwd}@{self.host}:{self.port}/{self.name}"

    @computed_field
    @property
    def sync_url(self) -> str:
        pwd = self.password.get_secret_value()
        return f"postgresql+psycopg2://{self.user}:{pwd}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: SecretStr | None = None
    ssl: bool = False

    @computed_field
    @property
    def url(self) -> str:
        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password.get_secret_value()}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # App-level
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: SecretStr
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    cors_origins: list[AnyHttpUrl] = []

    # Nested
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()

    @computed_field
    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached settings instance. Call once at startup."""
    return AppSettings()
```

Corresponding `.env` file:

```dotenv
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=change-me-in-production

DATABASE__HOST=db.internal
DATABASE__PORT=5432
DATABASE__NAME=myapp
DATABASE__USER=appuser
DATABASE__PASSWORD=dbpassword
DATABASE__POOL_SIZE=10
DATABASE__MAX_OVERFLOW=20

REDIS__HOST=redis.internal
REDIS__PASSWORD=redispassword
REDIS__SSL=true

ALLOWED_HOSTS=["myapp.com","www.myapp.com"]
CORS_ORIGINS=["https://myapp.com"]
```

## Tips and Gotchas

- **Lists and dicts from env**: Pydantic parses JSON-formatted strings. `ALLOWED_HOSTS=["a","b"]` works; `ALLOWED_HOSTS=a,b` does not for `list[str]`.
- **`env_prefix` applies to top-level fields only** -- nested model fields still use the `__` delimiter from the nested model's own name, not the prefix.
- **`SecretStr` in nested models**: Pydantic unwraps and re-wraps secret values correctly across nesting levels.
- **Docker Compose**: Use `env_file:` in compose to mirror the `.env` file without `__` flattening -- or pass vars directly and rely on the delimiter.
- **`@lru_cache` for settings**: Wrap `AppSettings()` in an `@lru_cache(maxsize=1)` function to avoid re-reading the filesystem on every access.
