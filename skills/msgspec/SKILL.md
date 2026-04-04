---
name: msgspec
description: "Auto-activate for msgspec imports, msgspec.Struct definitions, msgspec.json/msgpack usage. High-performance Python serialization and validation library: Struct definitions, Meta constraints, tagged unions, enc_hook/dec_hook, convert(). Produces msgspec Structs, serialization codecs, validation schemas, and type-safe conversion patterns. Use when: defining data models with msgspec, serializing/deserializing JSON or MessagePack, validating data with Meta constraints, building discriminated unions, or converting dicts/objects with msgspec.convert(). Not for Pydantic models, dataclasses, or attrs -- msgspec has its own patterns."
---

# msgspec Skill

msgspec is a high-performance Python library for serialization, deserialization, and validation. Structs are ~5x more memory-efficient than regular classes and serialize faster than Pydantic or dataclasses.

## Code Style Rules

- Use PEP 604 for unions: `T | None` (not `Optional[T]`)
- **Never** use `from __future__ import annotations` -- breaks msgspec runtime type resolution
- Always annotate all fields; msgspec requires type annotations
- Use `kw_only=True` for Structs with more than 2 fields

## Quick Reference

### Struct Definition

```python
import msgspec

# Basic struct
class User(msgspec.Struct):
    id: int
    name: str
    email: str | None = None

# Performance options
class Event(msgspec.Struct, frozen=True, gc=False):
    """frozen=True: immutable + hashable. gc=False: skip GC for short-lived objects."""
    event_type: str
    payload: dict[str, object]

# Keyword-only (recommended for >2 fields)
class Config(msgspec.Struct, kw_only=True):
    host: str
    port: int = 5432
    ssl: bool = False

# Array-like encoding (tuple encoding, more compact)
class Point(msgspec.Struct, array_like=True):
    x: float
    y: float

# Rename fields for serialization
class ApiResponse(msgspec.Struct, rename="camel"):
    user_id: int         # serialized as "userId"
    created_at: str      # serialized as "createdAt"

# Reject unknown fields at API boundaries
class StrictInput(msgspec.Struct, forbid_unknown_fields=True):
    name: str
    value: int
```

### Validation Constraints

```python
from typing import Annotated
import msgspec
from msgspec import Meta

class Product(msgspec.Struct):
    name: Annotated[str, Meta(min_length=1, max_length=100)]
    price: Annotated[float, Meta(gt=0)]
    quantity: Annotated[int, Meta(ge=0, le=10_000)]
    sku: Annotated[str, Meta(pattern=r"^[A-Z]{2}-\d{4}$")]
    weight_kg: Annotated[float, Meta(multiple_of=0.001)]

# Reusable constraint aliases
PositiveInt = Annotated[int, Meta(gt=0)]
NonEmptyStr = Annotated[str, Meta(min_length=1)]
Percentage = Annotated[float, Meta(ge=0.0, le=100.0)]

class Order(msgspec.Struct):
    id: PositiveInt
    label: NonEmptyStr
    discount: Percentage = 0.0
```

### Serialization

```python
import msgspec

# JSON -- singleton encoder/decoder (cache these!)
encoder = msgspec.json.Encoder()
decoder = msgspec.json.Decoder(User)

data = encoder.encode(user)          # bytes
user = decoder.decode(b'{"id":1,"name":"Alice"}')

# Functional API (convenience, slightly slower)
data = msgspec.json.encode(user)
user = msgspec.json.decode(b'...', type=User)

# MessagePack (binary, more compact)
data = msgspec.msgpack.encode(user)
user = msgspec.msgpack.decode(data, type=User)

# Custom hooks for non-native types (datetime, UUID, Decimal)
from datetime import datetime
import uuid

def enc_hook(obj: object) -> object:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Unsupported type: {type(obj)}")

def dec_hook(type: type, obj: object) -> object:
    if type is datetime:
        return datetime.fromisoformat(obj)
    if type is uuid.UUID:
        return uuid.UUID(obj)
    raise TypeError(f"Unsupported type: {type}")

encoder = msgspec.json.Encoder(enc_hook=enc_hook)
decoder = msgspec.json.Decoder(MyStruct, dec_hook=dec_hook)
```

### Type Coercion with convert()

```python
import msgspec

raw = {"id": "42", "name": "Alice"}  # id is a string

# Strict mode (default): raises on type mismatch
user = msgspec.convert(raw, User)  # ValidationError: id must be int

# Lax mode: coerces compatible types
user = msgspec.convert(raw, User, strict=False)  # id coerced to 42

# str_keys: dict keys are strings (useful for JSON-loaded dicts)
data = {"1": "Alice", "2": "Bob"}
result = msgspec.convert(data, dict[int, str], str_keys=True)

# Convert with dec_hook for custom types
user = msgspec.convert(raw, UserWithUUID, dec_hook=dec_hook)

# Convert dataclass/dict/object to Struct
from dataclasses import dataclass

@dataclass
class LegacyUser:
    id: int
    name: str

legacy = LegacyUser(id=1, name="Alice")
user = msgspec.convert(msgspec.structs.asdict(legacy), User)
# Or directly:
user = msgspec.convert(legacy, User)
```

### Dynamic Struct Creation

```python
import msgspec

# Runtime struct from field definitions
fields = [
    ("id", int),
    ("name", str),
    ("score", Annotated[float, Meta(ge=0.0)]),
]
DynamicModel = msgspec.defstruct("DynamicModel", fields, kw_only=True)

# With defaults
fields_with_defaults = [
    ("id", int),
    ("active", bool, True),   # (name, type, default)
]
FlexModel = msgspec.defstruct("FlexModel", fields_with_defaults)
```

### Tagged Unions (Discriminated Unions)

```python
import msgspec
from typing import Literal

# Default tag field is "type", tag value is the class name
class Dog(msgspec.Struct, tag=True):
    name: str
    breed: str

class Cat(msgspec.Struct, tag=True):
    name: str
    indoor: bool

Animal = Dog | Cat

# Deserialize: inspects "type" field to pick correct class
animal = msgspec.json.decode(b'{"type":"Dog","name":"Rex","breed":"Lab"}', type=Animal)

# Custom tag values
class CreateEvent(msgspec.Struct, tag="create"):
    resource: str

class DeleteEvent(msgspec.Struct, tag="delete"):
    resource: str
    soft: bool = True

Event = CreateEvent | DeleteEvent

# Custom tag field name
class V1Request(msgspec.Struct, tag="v1", tag_field="version"):
    payload: str

class V2Request(msgspec.Struct, tag="v2", tag_field="version"):
    payload: str
    metadata: dict[str, str] = {}

Request = V1Request | V2Request
```

<workflow>

## Workflow

### Step 1: Define Structs

Create msgspec Structs for all data shapes. Use `kw_only=True` for Structs with more than 2 fields. Use `frozen=True` for immutable value objects. Use `forbid_unknown_fields=True` for API-boundary input validation.

### Step 2: Add Constraints

Annotate fields with `Annotated[Type, Meta(...)]` for numeric ranges, string lengths, and regex patterns. Define reusable constraint aliases at module level to avoid repetition.

### Step 3: Choose Serialization Strategy

Use `msgspec.json` for JSON APIs and `msgspec.msgpack` for binary protocols or internal messaging. Instantiate `Encoder`/`Decoder` once at module level as singletons. Add `enc_hook`/`dec_hook` for custom types (datetime, UUID, Decimal, Enum).

### Step 4: Handle Polymorphism

Use tagged unions (`tag=True` or `tag="value"`) for discriminated unions. Define a union type alias (`Event = CreateEvent | DeleteEvent`) and decode against it. Use `tag_field` to customize the discriminator field name.

### Step 5: Validate

Test round-trip encode/decode. Confirm `ValidationError` is raised for constraint violations. Verify tag dispatch selects the correct Struct type for all union variants.

</workflow>

<guardrails>

## Guardrails

- **Always annotate all fields** -- msgspec requires type annotations; unannotated fields are ignored silently.
- **Cache Encoder/Decoder as singletons** -- instantiation is expensive; create once at module level and reuse.
- **Use `kw_only=True` for Structs with >2 fields** -- prevents positional argument confusion and makes instantiation self-documenting.
- **Use `forbid_unknown_fields=True` at API boundaries** -- rejects payloads with unexpected keys, preventing silent data loss.
- **Prefer `Meta` constraints over manual validation** -- zero runtime overhead; constraints are checked during decode, not after.
- **Use `gc=False` for short-lived, non-circular objects** -- eliminates GC overhead for hot-path objects like request/response shapes.
- **Tagged unions for polymorphism** -- faster than manual dispatch and eliminates `isinstance` chains.
- **Never use `from __future__ import annotations`** -- deferred annotation evaluation breaks msgspec's runtime type introspection.
- **Use `strict=False` only at trust boundaries** -- lax coercion is useful for converting legacy dicts but can mask type errors in internal code.

</guardrails>

<validation>

### Validation Checkpoint

Before delivering msgspec code, verify:

- [ ] All Struct fields have explicit type annotations
- [ ] No `from __future__ import annotations` anywhere in the module
- [ ] Encoder/Decoder instances are module-level singletons (not created per-request)
- [ ] API-boundary Structs use `forbid_unknown_fields=True`
- [ ] Numeric/string constraints use `Meta` (not manual `if` checks)
- [ ] `enc_hook`/`dec_hook` handle all non-native types used in Structs
- [ ] Tagged union tag values are unique across all variants in a union
- [ ] `kw_only=True` on Structs with more than 2 fields

</validation>

<example>

## Example

**Task:** Define an event system with tagged unions, constraints, and JSON serialization.

```python
from __future__ import annotations  # DO NOT DO THIS -- breaks msgspec
```

```python
# events.py
from typing import Annotated, Literal
from datetime import datetime
import uuid
import msgspec
from msgspec import Meta

# --- Constraint aliases ---
NonEmptyStr = Annotated[str, Meta(min_length=1, max_length=255)]
PositiveInt = Annotated[int, Meta(gt=0)]

# --- Event variants (tagged union) ---
class UserCreatedEvent(msgspec.Struct, tag="user.created", tag_field="event_type", kw_only=True, gc=False):
    event_id: uuid.UUID
    user_id: PositiveInt
    email: NonEmptyStr
    occurred_at: datetime

class UserDeletedEvent(msgspec.Struct, tag="user.deleted", tag_field="event_type", kw_only=True, gc=False):
    event_id: uuid.UUID
    user_id: PositiveInt
    occurred_at: datetime
    reason: str | None = None

UserEvent = UserCreatedEvent | UserDeletedEvent

# --- Custom hooks for datetime and UUID ---
def enc_hook(obj: object) -> object:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Unsupported type: {type(obj)}")

def dec_hook(type: type, obj: object) -> object:
    if type is datetime:
        return datetime.fromisoformat(obj)
    if type is uuid.UUID:
        return uuid.UUID(obj)
    raise TypeError(f"Unsupported type: {type}")

# --- Singleton codec ---
_encoder = msgspec.json.Encoder(enc_hook=enc_hook)
_decoder = msgspec.json.Decoder(UserEvent, dec_hook=dec_hook)

def encode_event(event: UserEvent) -> bytes:
    return _encoder.encode(event)

def decode_event(data: bytes) -> UserEvent:
    return _decoder.decode(data)

# --- Usage ---
event = UserCreatedEvent(
    event_id=uuid.uuid4(),
    user_id=42,
    email="alice@example.com",
    occurred_at=datetime.utcnow(),
)
payload = encode_event(event)
# b'{"event_type":"user.created","event_id":"...","user_id":42,"email":"alice@example.com","occurred_at":"..."}'

recovered = decode_event(payload)
assert isinstance(recovered, UserCreatedEvent)
```

</example>

---

## References Index

For detailed guides and reference tables, refer to the following documents in `references/`:

- **[Meta Constraints Reference](references/constraints.md)** -- Full table of all Meta constraint parameters with examples for numeric, string, bytes, and OpenAPI metadata.
- **[Tagged Union Patterns](references/tagged-unions.md)** -- Discriminated union patterns: default tags, custom tag fields/values, nested unions, API versioning, and event systems.

---

## Official References

- <https://jcristharif.com/msgspec/>
- <https://jcristharif.com/msgspec/structs.html>
- <https://jcristharif.com/msgspec/constraints.html>
- <https://jcristharif.com/msgspec/json.html>
- <https://jcristharif.com/msgspec/msgpack.html>
- <https://jcristharif.com/msgspec/converters.html>
- <https://jcristharif.com/msgspec/api.html>
- <https://github.com/jcrist/msgspec>

## Shared Styleguide Baseline

- Use shared styleguides for generic language/framework rules to reduce duplication in this skill.
- [General Principles](https://github.com/cofin/flow/blob/main/templates/styleguides/general.md)
- [Python](https://github.com/cofin/flow/blob/main/templates/styleguides/languages/python.md)
- Keep this skill focused on tool-specific workflows, edge cases, and integration details.
