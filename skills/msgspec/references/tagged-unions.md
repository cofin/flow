# msgspec Tagged Union Patterns

Tagged unions (discriminated unions) let msgspec select the correct Struct type during decoding based on a tag field in the payload. They replace manual `isinstance` dispatch and are faster than runtime type inspection.

## How It Works

When a union type contains multiple Structs that all declare a `tag`, msgspec reads the tag field from the incoming payload and routes to the matching Struct class. Tag matching happens before field validation.

---

## Default Tags (Class Name as Tag Value)

Using `tag=True` makes the class name the tag value, and the tag field name defaults to `"type"`.

```python
import msgspec

class Dog(msgspec.Struct, tag=True):
    name: str
    breed: str

class Cat(msgspec.Struct, tag=True):
    name: str
    indoor: bool

class Bird(msgspec.Struct, tag=True):
    name: str
    wingspan_cm: float

Animal = Dog | Cat | Bird

# Encode
dog = Dog(name="Rex", breed="Labrador")
data = msgspec.json.encode(dog)
# b'{"type":"Dog","name":"Rex","breed":"Labrador"}'

# Decode -- tag field "type" dispatches to Dog
animal = msgspec.json.decode(
    b'{"type":"Dog","name":"Rex","breed":"Labrador"}',
    type=Animal,
)
assert isinstance(animal, Dog)
```

---

## Custom Tag Values

Use `tag="string"` or `tag=integer` to control the tag value independently of the class name. Useful for snake_case names, versioned identifiers, or when class names differ from protocol values.

```python
import msgspec

class CreateEvent(msgspec.Struct, tag="create"):
    resource_id: int
    created_by: str

class UpdateEvent(msgspec.Struct, tag="update"):
    resource_id: int
    updated_by: str
    changes: dict[str, object]

class DeleteEvent(msgspec.Struct, tag="delete"):
    resource_id: int
    deleted_by: str
    soft: bool = True

Event = CreateEvent | UpdateEvent | DeleteEvent

raw = b'{"type":"delete","resource_id":42,"deleted_by":"alice"}'
event = msgspec.json.decode(raw, type=Event)
assert isinstance(event, DeleteEvent)
assert event.resource_id == 42
```

---

## Custom Tag Field Name

Use `tag_field="field_name"` to change the discriminator field name from the default `"type"`. All variants in a union must use the same `tag_field`.

```python
import msgspec

class V1Request(msgspec.Struct, tag="v1", tag_field="version", kw_only=True):
    payload: str

class V2Request(msgspec.Struct, tag="v2", tag_field="version", kw_only=True):
    payload: str
    metadata: dict[str, str] = {}

class V3Request(msgspec.Struct, tag="v3", tag_field="version", kw_only=True):
    payload: str
    metadata: dict[str, str] = {}
    priority: int = 0

Request = V1Request | V2Request | V3Request

raw = b'{"version":"v2","payload":"hello","metadata":{"trace":"abc"}}'
req = msgspec.json.decode(raw, type=Request)
assert isinstance(req, V2Request)
```

---

## Integer Tag Values

Tags can be integers instead of strings, useful for binary protocols or compact representations.

```python
import msgspec
import msgspec.msgpack

class PingMessage(msgspec.Struct, tag=1):
    seq: int

class PongMessage(msgspec.Struct, tag=2):
    seq: int

class DataMessage(msgspec.Struct, tag=3):
    seq: int
    payload: bytes

Message = PingMessage | PongMessage | DataMessage

msg = DataMessage(seq=7, payload=b"\x01\x02\x03")
encoded = msgspec.msgpack.encode(msg)

decoded = msgspec.msgpack.decode(encoded, type=Message)
assert isinstance(decoded, DataMessage)
```

---

## Nested Unions

Unions can be nested inside other Structs.

```python
import msgspec
from typing import Literal

class TextContent(msgspec.Struct, tag="text"):
    text: str

class ImageContent(msgspec.Struct, tag="image"):
    url: str
    alt: str | None = None

class VideoContent(msgspec.Struct, tag="video"):
    url: str
    duration_s: float

Content = TextContent | ImageContent | VideoContent

class Post(msgspec.Struct, kw_only=True):
    id: int
    author: str
    content: Content   # union field -- dispatched at decode time

raw = b'''{
    "id": 1,
    "author": "alice",
    "content": {"type": "image", "url": "https://example.com/img.png", "alt": "A photo"}
}'''
post = msgspec.json.decode(raw, type=Post)
assert isinstance(post.content, ImageContent)
```

---

## Real-World Pattern: API Versioning

Use tagged unions to route versioned API requests to the appropriate handler without if/elif chains.

```python
import msgspec
from typing import Annotated
from msgspec import Meta

NonEmptyStr = Annotated[str, Meta(min_length=1)]

class CreateUserV1(msgspec.Struct, tag="v1", tag_field="api_version", kw_only=True):
    username: NonEmptyStr
    email: NonEmptyStr

class CreateUserV2(msgspec.Struct, tag="v2", tag_field="api_version", kw_only=True):
    username: NonEmptyStr
    email: NonEmptyStr
    display_name: str | None = None
    locale: str = "en"

CreateUserRequest = CreateUserV1 | CreateUserV2

_decoder = msgspec.json.Decoder(CreateUserRequest)

async def handle_create_user(body: bytes) -> dict:
    request = _decoder.decode(body)
    match request:
        case CreateUserV1(username=u, email=e):
            return {"version": 1, "username": u, "email": e}
        case CreateUserV2(username=u, email=e, display_name=d, locale=l):
            return {"version": 2, "username": u, "email": e, "display_name": d, "locale": l}
```

---

## Real-World Pattern: Event Bus / Message Queue

Use tagged unions to define all event types in one place and decode them generically.

```python
import msgspec
from datetime import datetime
import uuid

def enc_hook(obj: object) -> object:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Unsupported: {type(obj)}")

def dec_hook(type: type, obj: object) -> object:
    if type is datetime:
        return datetime.fromisoformat(obj)
    if type is uuid.UUID:
        return uuid.UUID(obj)
    raise TypeError(f"Unsupported: {type}")

class OrderPlaced(msgspec.Struct, tag="order.placed", tag_field="event_type", kw_only=True, gc=False):
    event_id: uuid.UUID
    order_id: uuid.UUID
    user_id: int
    total: float
    placed_at: datetime

class OrderShipped(msgspec.Struct, tag="order.shipped", tag_field="event_type", kw_only=True, gc=False):
    event_id: uuid.UUID
    order_id: uuid.UUID
    tracking_number: str
    shipped_at: datetime

class OrderCancelled(msgspec.Struct, tag="order.cancelled", tag_field="event_type", kw_only=True, gc=False):
    event_id: uuid.UUID
    order_id: uuid.UUID
    reason: str | None
    cancelled_at: datetime

OrderEvent = OrderPlaced | OrderShipped | OrderCancelled

_encoder = msgspec.json.Encoder(enc_hook=enc_hook)
_decoder = msgspec.json.Decoder(OrderEvent, dec_hook=dec_hook)

def publish_event(event: OrderEvent) -> bytes:
    return _encoder.encode(event)

def consume_event(data: bytes) -> OrderEvent:
    return _decoder.decode(data)

# Handler dispatch
async def handle_event(data: bytes) -> None:
    event = consume_event(data)
    match event:
        case OrderPlaced():
            await process_payment(event)
        case OrderShipped():
            await send_shipping_notification(event)
        case OrderCancelled():
            await issue_refund(event)
```

---

## Real-World Pattern: Command Pattern

Use tagged unions to represent commands, useful for CQRS or task queue systems.

```python
import msgspec
from typing import Annotated
from msgspec import Meta

PositiveInt = Annotated[int, Meta(gt=0)]

class SendEmailCommand(msgspec.Struct, tag="send_email", kw_only=True):
    to: str
    subject: str
    body: str

class GenerateReportCommand(msgspec.Struct, tag="generate_report", kw_only=True):
    report_type: str
    filters: dict[str, object] = {}
    requested_by: PositiveInt

class PurgeDataCommand(msgspec.Struct, tag="purge_data", kw_only=True):
    entity_type: str
    entity_ids: list[PositiveInt]
    requested_by: PositiveInt

Command = SendEmailCommand | GenerateReportCommand | PurgeDataCommand

_decoder = msgspec.json.Decoder(Command)

async def dispatch_command(payload: bytes) -> None:
    command = _decoder.decode(payload)
    match command:
        case SendEmailCommand(to=addr, subject=subj):
            await send_email(addr, subj, command.body)
        case GenerateReportCommand(report_type=rtype):
            await generate_report(rtype, command.filters)
        case PurgeDataCommand(entity_type=etype, entity_ids=ids):
            await purge_entities(etype, ids)
```

---

## Common Mistakes

### All union variants must have the same tag_field

```python
# WRONG -- mixed tag_field values cause a decode error
class A(msgspec.Struct, tag="a", tag_field="type"): ...
class B(msgspec.Struct, tag="b", tag_field="kind"): ...  # different tag_field!
AB = A | B  # will fail at decode

# CORRECT -- consistent tag_field across all variants
class A(msgspec.Struct, tag="a", tag_field="kind"): ...
class B(msgspec.Struct, tag="b", tag_field="kind"): ...
AB = A | B
```

### Tag values must be unique within a union

```python
# WRONG -- duplicate tag causes ambiguity
class A(msgspec.Struct, tag="same"): ...
class B(msgspec.Struct, tag="same"): ...  # collision!

# CORRECT
class A(msgspec.Struct, tag="type_a"): ...
class B(msgspec.Struct, tag="type_b"): ...
```

### Without tag, union decoding falls back to structural matching (slower)

```python
# Without tag= on Struct, msgspec tries each type in order -- error-prone
# Always use tag= for polymorphic unions where types share fields
```
