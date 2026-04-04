# Pydantic V1 → V2 Migration Guide

Pydantic v2 is a ground-up rewrite with a Rust core. Most APIs changed. This guide maps every common V1 pattern to its V2 equivalent and documents breaking changes and gotchas.

## Full API Mapping Table

### Model Configuration

| V1 | V2 |
|----|-----|
| `class Config: orm_mode = True` | `model_config = ConfigDict(from_attributes=True)` |
| `class Config: extra = "forbid"` | `model_config = ConfigDict(extra="forbid")` |
| `class Config: validate_assignment = True` | `model_config = ConfigDict(validate_assignment=True)` |
| `class Config: arbitrary_types_allowed = True` | `model_config = ConfigDict(arbitrary_types_allowed=True)` |
| `class Config: use_enum_values = True` | `model_config = ConfigDict(use_enum_values=True)` |
| `class Config: allow_population_by_field_name = True` | `model_config = ConfigDict(populate_by_name=True)` |
| `class Config: underscore_attrs_are_private = True` | `model_config = ConfigDict(...)` + use `PrivateAttr` explicitly |
| `class Config: schema_extra = {...}` | `model_config = ConfigDict(json_schema_extra={...})` |
| `class Config: alias_generator = ...` | `model_config = ConfigDict(alias_generator=...)` |
| `class Config: fields = {"x": {"alias": "y"}}` | `x: T = Field(alias="y")` |

### Validators

| V1 | V2 |
|----|-----|
| `@validator("field")` | `@field_validator("field")` |
| `@validator("field", pre=True)` | `@field_validator("field", mode="before")` |
| `@validator("field", always=True)` | `@field_validator("field")` (always runs in V2) |
| `@validator("field", each_item=True)` | Validate inside the validator manually or use `@field_validator` on items |
| `@root_validator` | `@model_validator(mode="before")` or `@model_validator(mode="after")` |
| `@root_validator(pre=True)` | `@model_validator(mode="before")` |
| `@root_validator(pre=False)` / `@root_validator` | `@model_validator(mode="after")` |
| `cls` as first arg in `@validator` | `@classmethod` decorator required + `cls` first arg |
| `values` dict param in `@root_validator` | Instance `self` (mode='after') or raw `data` dict (mode='before') |

### Serialization

| V1 | V2 |
|----|-----|
| `.dict()` | `.model_dump()` |
| `.dict(exclude_unset=True)` | `.model_dump(exclude_unset=True)` |
| `.dict(by_alias=True)` | `.model_dump(by_alias=True)` |
| `.json()` | `.model_dump_json()` |
| `.json(by_alias=True)` | `.model_dump_json(by_alias=True)` |
| `.schema()` | `.model_json_schema()` |
| `.schema_json()` | `json.dumps(.model_json_schema())` |

### Parsing / Instantiation

| V1 | V2 |
|----|-----|
| `MyModel.parse_obj(data)` | `MyModel.model_validate(data)` |
| `MyModel.parse_raw(json_str)` | `MyModel.model_validate_json(json_str)` |
| `MyModel.parse_file(path)` | Read file + `model_validate_json(content)` |
| `MyModel.from_orm(obj)` | `MyModel.model_validate(obj, from_attributes=True)` or set `ConfigDict(from_attributes=True)` |
| `MyModel.construct(**kwargs)` | `MyModel.model_construct(**kwargs)` |
| `MyModel.copy()` | `MyModel.model_copy()` |
| `MyModel.copy(update={...})` | `MyModel.model_copy(update={...})` |

### Introspection

| V1 | V2 |
|----|-----|
| `MyModel.__fields__` | `MyModel.model_fields` |
| `MyModel.__fields_set__` | `instance.model_fields_set` |
| `MyModel.__validators__` | (removed — use `MyModel.__pydantic_validator__`) |
| `MyModel.schema()` | `MyModel.model_json_schema()` |
| `MyModel.__config__` | `MyModel.model_config` |

### Custom Types

| V1 | V2 |
|----|-----|
| `class MyType: @classmethod def __get_validators__(cls)` | `Annotated[T, BeforeValidator(...)]` or implement `__get_pydantic_core_schema__` |
| `@validator` + `arbitrary_types_allowed` | `Annotated[T, BeforeValidator(fn)]` with `ConfigDict(arbitrary_types_allowed=True)` |

### BaseSettings (pydantic-settings)

| V1 (built-in) | V2 (pydantic-settings package) |
|---------------|-------------------------------|
| `from pydantic import BaseSettings` | `from pydantic_settings import BaseSettings` |
| `class Config: env_nested_delimiter = "__"` | `model_config = SettingsConfigDict(env_nested_delimiter="__")` |
| `class Config: env_file = ".env"` | `model_config = SettingsConfigDict(env_file=".env")` |

**Note**: `pydantic-settings` is a separate package in V2. Install with `pip install pydantic-settings`.

---

## Breaking Changes and Gotchas

### `@validator` → `@field_validator` requires `@classmethod`

```python
# V1 — no @classmethod needed
@validator("name")
def validate_name(cls, v):
    return v.strip()

# V2 — @classmethod is required
@field_validator("name")
@classmethod
def validate_name(cls, v: str) -> str:
    return v.strip()
```

### `@root_validator` mode semantics changed

```python
# V1
@root_validator(pre=True)
def check_raw(cls, values):
    return values

@root_validator
def check_after(cls, values):
    # values is a dict even in post mode
    return values

# V2
@model_validator(mode="before")
@classmethod
def check_raw(cls, data: dict) -> dict:
    return data

@model_validator(mode="after")
def check_after(self) -> "MyModel":
    # self is the fully constructed model instance
    return self
```

### `mode="after"` receives instance, not dict

In V1, `@root_validator` always gave you a dict of `values`. In V2, `mode="after"` gives you the actual model instance (`self`). Access fields as attributes.

### `@validator` `values` param is gone

V1 validators could access previously-validated fields via the `values` kwarg:

```python
# V1
@validator("end_date")
def check_end_after_start(cls, v, values):
    if "start_date" in values and v < values["start_date"]:
        raise ValueError("end must be after start")
    return v
```

In V2, use `@model_validator(mode="after")` for cross-field validation instead:

```python
# V2
@model_validator(mode="after")
def check_dates(self) -> "MyModel":
    if self.end_date < self.start_date:
        raise ValueError("end must be after start")
    return self
```

### `Field` default behavior

In V1, `Field(alias="x")` alone enabled population by alias. In V2, you must also set `ConfigDict(populate_by_name=True)` if you want to populate by the Python field name too.

```python
# V2
class MyModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    my_field: str = Field(alias="myField")

MyModel(myField="a")   # works
MyModel(my_field="a")  # also works (because populate_by_name=True)
```

### `model_dump()` returns Python objects, not JSON-safe types

`model_dump()` may return `datetime`, `UUID`, `Decimal`, etc. Use `model_dump(mode="json")` or `model_dump_json()` when you need JSON-serializable output.

### `model_construct()` skips validation

`model_construct()` (V2) and `construct()` (V1) both skip validation. Use only when you know the data is already valid (e.g., reading from a trusted database).

### `from __future__ import annotations` breaks V2

Pydantic v2 relies on runtime type evaluation. `from __future__ import annotations` turns all annotations into strings, breaking validators, DI, and schema generation. Do not use it with Pydantic models.

### Constrained types changed

```python
# V1
from pydantic import constr, conint, confloat

name: constr(min_length=1, max_length=50)
age: conint(gt=0, le=150)

# V2 — use Field() or Annotated
from pydantic import Field
from typing import Annotated

name: Annotated[str, Field(min_length=1, max_length=50)]
age: Annotated[int, Field(gt=0, le=150)]
```

### `ValidationError` format changed

V2 `ValidationError.errors()` returns a list of dicts with a new structure. The `loc` field is now a tuple of strings/ints (same as V1), but `type` uses dot-separated identifiers (e.g., `"string_too_short"` instead of `"value_error.any_str.min_length"`). Update any code that pattern-matches on error types.

---

## Coexistence Patterns During Migration

### Strategy 1: Model-by-Model Migration

Migrate one model at a time. V1 and V2 models can coexist in the same codebase if they are not mixed within the same inheritance hierarchy.

```python
# Keep V1 models temporarily
from pydantic.v1 import BaseModel as V1BaseModel

class LegacyModel(V1BaseModel):   # uses V1 semantics
    class Config:
        orm_mode = True

# New models use V2
from pydantic import BaseModel, ConfigDict

class NewModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

Pydantic v2 ships a `pydantic.v1` compatibility shim that re-exports the entire V1 API. This lets you migrate files incrementally without breaking existing code.

### Strategy 2: `pydantic.v1` Shim

```python
# Before migration — swap import, no other changes needed yet
from pydantic.v1 import BaseModel, validator, root_validator, Field

class OldModel(BaseModel):
    name: str

    @validator("name")
    def strip_name(cls, v):
        return v.strip()
```

This is a stopgap. The V1 shim will be removed in a future version. Use it to unblock upgrades, not as a permanent solution.

### Strategy 3: Adapter Layer

Wrap V1 model instantiation behind a factory so you can swap implementations:

```python
def create_user(data: dict) -> UserModel:
    return UserModel.model_validate(data)  # V2
    # return UserModel.parse_obj(data)     # V1 — swap when migrating
```

---

## Migration Checklist

- [ ] Replace `from pydantic import BaseSettings` with `from pydantic_settings import BaseSettings`
- [ ] Replace all `class Config` blocks with `model_config = ConfigDict(...)`
- [ ] Replace `orm_mode = True` → `from_attributes=True`
- [ ] Replace `@validator` → `@field_validator` (add `@classmethod`)
- [ ] Replace `@root_validator(pre=True)` → `@model_validator(mode="before")` (add `@classmethod`)
- [ ] Replace `@root_validator` → `@model_validator(mode="after")` (no `@classmethod`; use `self`)
- [ ] Replace `.dict()` → `.model_dump()`
- [ ] Replace `.json()` → `.model_dump_json()`
- [ ] Replace `.parse_obj()` → `.model_validate()`
- [ ] Replace `.parse_raw()` → `.model_validate_json()`
- [ ] Replace `.copy()` → `.model_copy()`
- [ ] Replace `.construct()` → `.model_construct()`
- [ ] Replace `__fields__` → `model_fields`
- [ ] Replace `constr/conint/confloat` → `Annotated[T, Field(...)]`
- [ ] Remove `from __future__ import annotations` from model files
- [ ] Update `ValidationError` error type string matching in tests/error handlers
- [ ] Add `populate_by_name=True` to `ConfigDict` if fields use aliases and need dual-name access
