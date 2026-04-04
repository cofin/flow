---
name: pydantic
description: "Auto-activate for pydantic imports, BaseModel, BaseSettings, pydantic_settings. Pydantic v2 data validation and settings management: field validators, model validators, serialization, TypeAdapter, BaseSettings env config. Produces validated Pydantic models, settings classes, custom types, and migration-safe patterns. Use when: defining data models with validation, managing environment configuration, validating external data, or migrating from Pydantic v1 to v2. Not for msgspec Structs or dataclasses -- Pydantic has its own patterns."
---

# Pydantic Skill

Pydantic v2 is a high-performance Python data validation library with first-class support for type hints, environment configuration via `BaseSettings`, and a complete rewrite from v1 with significant API changes.

## Code Style Rules

- Use PEP 604 for unions: `T | None` (not `Optional[T]`)
- Use `model_config = ConfigDict(...)` not inner `class Config`
- Use `model_validate()` for untrusted external input (not `__init__`)
- Use `Annotated[T, Field(...)]` over `Field(...)` as a default value

## Quick Reference

### ConfigDict

```python
from pydantic import BaseModel, ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,       # replaces orm_mode=True (v1)
        extra="forbid",             # "allow", "ignore", or "forbid"
        validate_assignment=True,   # re-validate on attribute set
        arbitrary_types_allowed=True,
        populate_by_name=True,      # allow field name or alias
        str_strip_whitespace=True,
        frozen=True,                # make model immutable
    )
```

### Validators

```python
from pydantic import BaseModel, field_validator, model_validator, computed_field

class Order(BaseModel):
    quantity: int
    unit_price: float
    discount: float = 0.0

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity must be > 0")
        return v

    @field_validator("discount")
    @classmethod
    def discount_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("discount must be between 0 and 1")
        return v

    @model_validator(mode="before")
    @classmethod
    def check_raw_data(cls, data: dict) -> dict:
        # runs before individual field validation
        if "unit_price" in data and data["unit_price"] < 0:
            raise ValueError("unit_price cannot be negative")
        return data

    @model_validator(mode="after")
    def check_total(self) -> "Order":
        # runs after all fields are validated; self is fully populated
        if self.quantity * self.unit_price > 1_000_000:
            raise ValueError("order total exceeds limit")
        return self

    @computed_field
    @property
    def total(self) -> float:
        return self.quantity * self.unit_price * (1 - self.discount)
```

### Serialization

```python
model = Order(quantity=2, unit_price=9.99)

# model_dump options
model.model_dump()
model.model_dump(by_alias=True)          # use field aliases in output
model.model_dump(exclude_unset=True)     # omit fields not explicitly set
model.model_dump(exclude_none=True)      # omit None-valued fields
model.model_dump(include={"quantity"})   # only these fields
model.model_dump(exclude={"discount"})   # all except these fields
model.model_dump(mode="json")            # JSON-serializable types

# JSON string
model.model_dump_json()
model.model_dump_json(by_alias=True, exclude_none=True)

# Custom field serializer
from pydantic import field_serializer

class Item(BaseModel):
    price: float

    @field_serializer("price")
    def serialize_price(self, v: float) -> str:
        return f"${v:.2f}"

# Custom model serializer
from pydantic import model_serializer

class Item(BaseModel):
    name: str
    price: float

    @model_serializer
    def custom_serialize(self) -> dict:
        return {"label": self.name, "cost": self.price}
```

### TypeAdapter — Bulk Validation

```python
from pydantic import TypeAdapter

# Significantly faster than calling MyModel(...) in a loop
adapter = TypeAdapter(list[MyModel])
items = adapter.validate_python(raw_list)          # from Python objects
items = adapter.validate_json(json_string)         # from JSON bytes/str

# Also works for non-model types
int_adapter = TypeAdapter(int)
int_adapter.validate_python("42")  # returns 42
```

### Custom Types — Annotated Pattern

```python
from typing import Annotated
from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema
from pydantic.functional_validators import AfterValidator

def parse_comma_list(v: str | list) -> list[str]:
    if isinstance(v, str):
        return [item.strip() for item in v.split(",")]
    return v

def validate_positive(v: int) -> int:
    assert v > 0, "must be positive"
    return v

CommaList = Annotated[
    list[str],
    BeforeValidator(parse_comma_list),
    WithJsonSchema({"type": "string", "description": "Comma-separated values"}),
]

PositiveInt = Annotated[int, AfterValidator(validate_positive)]

TagList = Annotated[
    list[str],
    BeforeValidator(parse_comma_list),
    PlainSerializer(lambda v: ",".join(v), return_type=str),
]
```

### BaseSettings — Environment Configuration

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",   # DATABASE__HOST → database.host
        case_sensitive=False,
        extra="ignore",
    )

    debug: bool = False
    secret_key: str
    allowed_hosts: list[str] = ["localhost"]

settings = AppSettings()   # reads from env + .env file
```

Priority chain: **explicit args > env vars > .env file > defaults**

See [BaseSettings Deep Reference](references/basesettings.md) for nested models, secrets directory, multiple env files, and custom sources.

### PrivateAttr — Non-Validated Internal State

```python
from pydantic import BaseModel, PrivateAttr

class Connection(BaseModel):
    host: str
    port: int = 5432
    _client: object = PrivateAttr(default=None)

    def connect(self) -> None:
        self._client = create_client(self.host, self.port)
```

### Constrained Types via Field

```python
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0, le=999_999.99)
    stock: int = Field(ge=0)
    sku: str = Field(pattern=r"^[A-Z]{3}-\d{4}$")
    tags: list[str] = Field(min_length=0, max_length=10)
```

### Special Types

```python
from pydantic import EmailStr, SecretStr, AnyUrl, AnyHttpUrl
from pydantic import PastDate, FutureDate, AwareDatetime, ByteSize

class UserProfile(BaseModel):
    email: EmailStr              # validates email format
    password: SecretStr          # hidden in repr/serialization
    website: AnyHttpUrl | None = None
    birth_date: PastDate | None = None
    appointment: AwareDatetime | None = None  # timezone-aware datetime
    avatar_size: ByteSize = "5MB"             # "5MB", "1GiB", etc.
```

### V1 → V2 Migration Quick Reference

| V1 | V2 |
|----|-----|
| `class Config: orm_mode = True` | `model_config = ConfigDict(from_attributes=True)` |
| `@root_validator` | `@model_validator(mode='before'/'after')` |
| `@validator` | `@field_validator` |
| `.dict()` | `.model_dump()` |
| `.json()` | `.model_dump_json()` |
| `.parse_obj(data)` | `.model_validate(data)` |
| `.parse_raw(json_str)` | `.model_validate_json(json_str)` |
| `__fields__` | `model_fields` |
| `Field(alias=..., allow_population_by_field_name=True)` | `Field(alias=...) + ConfigDict(populate_by_name=True)` |

See [V1→V2 Migration Guide](references/migration-v1-v2.md) for full mapping, breaking changes, and coexistence patterns.

### Performance

```python
# Prefer model_validate() for untrusted/external data — skips Python __init__ overhead
obj = MyModel.model_validate(raw_dict)

# TypeAdapter for batch operations — do NOT use list comprehension with __init__
adapter = TypeAdapter(list[MyModel])
items = adapter.validate_python(raw_list)   # single validation pass

# Selective model_dump — avoid serializing the whole model if you only need a few fields
subset = obj.model_dump(include={"id", "name"})
```

<workflow>

## Workflow

### Step 1: Define Models

Create `BaseModel` subclasses with type-annotated fields. Use `ConfigDict` at the top of each model to set behavior. Prefer `Annotated[T, Field(...)]` over `Field(...)` as default values for reusability.

### Step 2: Add Validators

Add `@field_validator` for single-field rules. Use `@model_validator(mode='before')` to preprocess raw input dicts and `@model_validator(mode='after')` for cross-field invariants on the fully constructed model. Add `@computed_field` for derived read-only properties.

### Step 3: Handle Serialization

Use `model_dump(exclude_unset=True)` when patching. Use `by_alias=True` when the API consumer expects camelCase or snake_case aliases. Use `@field_serializer` or `@model_serializer` for custom output formats.

### Step 4: Configure Settings

Create a `BaseSettings` subclass in `pydantic_settings` for environment-driven config. Set `env_nested_delimiter="__"` to support nested models from flat env vars. Load once at startup and inject as a dependency.

### Step 5: Validate

Run `mypy` or `pyright` with the pydantic plugin. Use `TypeAdapter` when validating collections for performance. Run tests to confirm validator error messages are user-friendly.

</workflow>

<guardrails>

## Guardrails

- **Use `ConfigDict` not inner `class Config`** -- `class Config` is the V1 pattern and silently ignored in some V2 contexts.
- **Use `model_validate()` for untrusted input** -- it is faster and safer than calling `__init__` directly; triggers full validation pipeline.
- **Use `BaseSettings` for environment configuration** -- never read `os.environ` manually in application code; BaseSettings handles type coercion, defaults, and `.env` loading.
- **Use `TypeAdapter` for bulk operations** -- never use a list comprehension calling `MyModel(...)` or `MyModel.model_validate(...)` in a loop; a single `TypeAdapter(list[MyModel]).validate_python(data)` is significantly faster.
- **Never mix V1 and V2 patterns in the same model** -- mixing `@validator` (V1) with `@field_validator` (V2) in the same class causes silent misbehavior or errors.
- **Use `Annotated[T, Field(...)]` over `Field(...)` as a default value** -- the `Annotated` pattern allows reuse as a type alias and avoids mutable default pitfalls.
- **Use `SecretStr` for passwords and tokens** -- prevents accidental leakage in logs, repr, and serialization.
- **Avoid `model_dump(mode='json')` in hot paths** -- use `model_dump_json()` directly when you need a JSON string; it skips the intermediate dict.

</guardrails>

<validation>

### Validation Checkpoint

Before delivering Pydantic code, verify:

- [ ] `model_config = ConfigDict(...)` used (not inner `class Config`)
- [ ] `model_validate()` used for external/untrusted data (not bare `__init__`)
- [ ] `TypeAdapter` used for bulk list/collection validation
- [ ] No V1 patterns (`@validator`, `@root_validator`, `.dict()`, `.json()`) in new code
- [ ] `BaseSettings` used for environment configuration, not `os.environ`
- [ ] Passwords/tokens use `SecretStr`
- [ ] `Annotated[T, Field(...)]` pattern used for constrained fields
- [ ] `@computed_field` used for derived properties (not plain `@property`)

</validation>

<example>

## Example

**Task:** User registration model with validation + app settings loaded from environment.

```python
from __future__ import annotations  # NOT used — pydantic needs runtime type eval

from typing import Annotated
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


# --- Reusable constrained type aliases ---
Username = Annotated[str, Field(min_length=3, max_length=32, pattern=r"^\w+$")]
Password = Annotated[SecretStr, Field(min_length=8)]


# --- Domain model ---
class UserRegistration(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: Username
    email: EmailStr
    password: Password
    confirm_password: Password

    @field_validator("username")
    @classmethod
    def username_not_reserved(cls, v: str) -> str:
        reserved = {"admin", "root", "system"}
        if v.lower() in reserved:
            raise ValueError(f"'{v}' is a reserved username")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "UserRegistration":
        if self.password != self.confirm_password:
            raise ValueError("passwords do not match")
        return self

    @computed_field
    @property
    def display_name(self) -> str:
        return self.username.capitalize()


# --- Settings from environment ---
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


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    debug: bool = False
    secret_key: SecretStr
    database: DatabaseSettings = DatabaseSettings()
    allowed_hosts: list[str] = ["localhost"]


# --- Usage ---
# Validate untrusted input
registration = UserRegistration.model_validate({
    "username": "alice",
    "email": "alice@example.com",
    "password": "s3cure!pw",
    "confirm_password": "s3cure!pw",
})

# Load settings once at startup
# DATABASE__HOST=db.prod DATABASE__PORT=5433 SECRET_KEY=xyz python app.py
settings = AppSettings()
db_url = settings.database.url
```

</example>

---

## References Index

For detailed guides and configuration examples, refer to the following documents in `references/`:

- **[BaseSettings Deep Reference](references/basesettings.md)** -- SettingsConfigDict options, nested models, secrets directory, multiple env files, custom sources, and full working example.
- **[V1→V2 Migration Guide](references/migration-v1-v2.md)** -- Full API mapping table, breaking changes, gotchas, and coexistence patterns during incremental migration.

---

## Official References

- <https://docs.pydantic.dev/latest/>
- <https://docs.pydantic.dev/latest/concepts/models/>
- <https://docs.pydantic.dev/latest/concepts/validators/>
- <https://docs.pydantic.dev/latest/concepts/serialization/>
- <https://docs.pydantic.dev/latest/concepts/pydantic_settings/>
- <https://docs.pydantic.dev/latest/migration/>
- <https://github.com/pydantic/pydantic>
- <https://github.com/pydantic/pydantic-settings>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
