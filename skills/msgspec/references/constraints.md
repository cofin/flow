# msgspec Meta Constraints Reference

`Meta` constraints are applied via `Annotated[Type, Meta(...)]`. They are evaluated at decode/convert time with zero runtime overhead — no validation code runs on already-valid data.

## Import

```python
from typing import Annotated
from msgspec import Meta
```

---

## Numeric Constraints

Applies to `int`, `float`, `Decimal`.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `gt` | Greater than (exclusive) | `Meta(gt=0)` → value > 0 |
| `ge` | Greater than or equal (inclusive) | `Meta(ge=0)` → value >= 0 |
| `lt` | Less than (exclusive) | `Meta(lt=100)` → value < 100 |
| `le` | Less than or equal (inclusive) | `Meta(le=100)` → value <= 100 |
| `multiple_of` | Value must be a multiple of N | `Meta(multiple_of=5)` → 0, 5, 10, ... |

```python
import msgspec
from typing import Annotated
from msgspec import Meta

# Positive integer (non-zero)
PositiveInt = Annotated[int, Meta(gt=0)]

# Non-negative integer (zero allowed)
NonNegInt = Annotated[int, Meta(ge=0)]

# Float in a closed range
Probability = Annotated[float, Meta(ge=0.0, le=1.0)]

# Percentage (0–100 inclusive)
Percentage = Annotated[float, Meta(ge=0.0, le=100.0)]

# Price with 0.01 granularity
Price = Annotated[float, Meta(gt=0.0, multiple_of=0.01)]

# Port number
Port = Annotated[int, Meta(ge=1, le=65535)]

# Bounded integer range
Rating = Annotated[int, Meta(ge=1, le=5)]

class Product(msgspec.Struct, kw_only=True):
    id: PositiveInt
    price: Price
    stock: NonNegInt
    rating: Rating = 3
```

---

## String Constraints

Applies to `str`.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `min_length` | Minimum character count (inclusive) | `Meta(min_length=1)` → non-empty |
| `max_length` | Maximum character count (inclusive) | `Meta(max_length=255)` → <= 255 chars |
| `pattern` | Regex pattern (full match via `re.search`) | `Meta(pattern=r"^\d{4}$")` |

```python
# Non-empty string
NonEmptyStr = Annotated[str, Meta(min_length=1)]

# Bounded non-empty string
ShortStr = Annotated[str, Meta(min_length=1, max_length=100)]

# Long text field
LongText = Annotated[str, Meta(max_length=10_000)]

# Email-like pattern (simple)
EmailStr = Annotated[str, Meta(pattern=r"^[^@]+@[^@]+\.[^@]+$")]

# Slug: lowercase letters, digits, hyphens
Slug = Annotated[str, Meta(pattern=r"^[a-z0-9-]+$", min_length=1, max_length=64)]

# SKU: exactly "XX-1234" format
SKU = Annotated[str, Meta(pattern=r"^[A-Z]{2}-\d{4}$")]

# UUID string format
UUIDStr = Annotated[str, Meta(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")]

class Article(msgspec.Struct, kw_only=True):
    slug: Slug
    title: ShortStr
    body: LongText
    author_email: EmailStr
```

---

## Bytes Constraints

Applies to `bytes`.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `min_length` | Minimum byte count (inclusive) | `Meta(min_length=16)` |
| `max_length` | Maximum byte count (inclusive) | `Meta(max_length=1024)` |

```python
# Fixed-size token (e.g., 32-byte secret)
Token = Annotated[bytes, Meta(min_length=32, max_length=32)]

# Bounded binary blob
Blob = Annotated[bytes, Meta(max_length=65536)]

class SecurePayload(msgspec.Struct):
    token: Token
    data: Blob
```

---

## Collection Constraints

Applies to `list`, `tuple`, `set`, `frozenset`, `dict`.

| Parameter | Description | Example |
|-----------|-------------|---------|
| `min_length` | Minimum number of elements | `Meta(min_length=1)` → non-empty list |
| `max_length` | Maximum number of elements | `Meta(max_length=100)` |

```python
# Non-empty list
NonEmptyList = Annotated[list[str], Meta(min_length=1)]

# Bounded list
Tags = Annotated[list[str], Meta(min_length=0, max_length=20)]

# Non-empty dict
NonEmptyDict = Annotated[dict[str, int], Meta(min_length=1)]

class TaggedItem(msgspec.Struct):
    name: str
    tags: Tags = []
```

---

## OpenAPI / JSON Schema Metadata

`Meta` also accepts fields that enrich generated JSON Schema (used by Litestar, FastAPI, and similar):

| Parameter | Description |
|-----------|-------------|
| `title` | Human-readable field title |
| `description` | Field description for docs |
| `examples` | List of example values |
| `extra_json_schema` | Raw dict merged into the JSON Schema output |

```python
UserId = Annotated[
    int,
    Meta(
        gt=0,
        title="User ID",
        description="Unique identifier for the user",
        examples=[1, 42, 9999],
    ),
]

# extra_json_schema for OpenAPI extensions or format hints
ISODate = Annotated[
    str,
    Meta(
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        extra_json_schema={"format": "date"},
    ),
]

class UserProfile(msgspec.Struct, kw_only=True):
    id: UserId
    joined: ISODate
    bio: Annotated[
        str | None,
        Meta(
            max_length=500,
            description="Optional user biography",
        ),
    ] = None
```

---

## Combining Multiple Constraints

All applicable parameters can be combined in a single `Meta` call:

```python
# Bounded, non-empty, patterned string
ProductCode = Annotated[
    str,
    Meta(
        min_length=3,
        max_length=20,
        pattern=r"^[A-Z0-9-]+$",
        title="Product Code",
        description="Uppercase alphanumeric product identifier",
        examples=["ABC-123", "XYZ-999"],
    ),
]

# Strictly bounded positive float with schema metadata
Latitude = Annotated[
    float,
    Meta(
        ge=-90.0,
        le=90.0,
        title="Latitude",
        description="WGS84 latitude coordinate",
        extra_json_schema={"format": "double"},
    ),
]

Longitude = Annotated[
    float,
    Meta(
        ge=-180.0,
        le=180.0,
        title="Longitude",
        description="WGS84 longitude coordinate",
        extra_json_schema={"format": "double"},
    ),
]

class Coordinate(msgspec.Struct, frozen=True, gc=False):
    lat: Latitude
    lon: Longitude
```

---

## Validation Error Behavior

When a constraint is violated during `decode()` or `convert()`, msgspec raises `msgspec.ValidationError` with a clear message:

```python
import msgspec

Price = Annotated[float, Meta(gt=0.0)]

class Item(msgspec.Struct):
    price: Price

try:
    msgspec.json.decode(b'{"price": -1.0}', type=Item)
except msgspec.ValidationError as e:
    print(e)
    # Expected `float` satisfying gt=0.0 - at `$.price`
```

Errors include the JSON path to the offending field, making them suitable for surfacing directly to API clients.

---

## Reusable Constraint Type Aliases (Recommended Pattern)

Define a `types.py` or `constraints.py` module with shared aliases:

```python
# myapp/types.py
from typing import Annotated
from msgspec import Meta

# Integers
PositiveInt = Annotated[int, Meta(gt=0)]
NonNegInt   = Annotated[int, Meta(ge=0)]
Port        = Annotated[int, Meta(ge=1, le=65535)]
Rating      = Annotated[int, Meta(ge=1, le=5)]

# Floats
Probability  = Annotated[float, Meta(ge=0.0, le=1.0)]
Percentage   = Annotated[float, Meta(ge=0.0, le=100.0)]
Price        = Annotated[float, Meta(gt=0.0, multiple_of=0.01)]

# Strings
NonEmptyStr  = Annotated[str, Meta(min_length=1)]
ShortStr     = Annotated[str, Meta(min_length=1, max_length=255)]
Slug         = Annotated[str, Meta(pattern=r"^[a-z0-9-]+$", min_length=1, max_length=64)]

# Collections
NonEmptyList = Annotated[list, Meta(min_length=1)]
```
