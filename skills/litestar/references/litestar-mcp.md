# Litestar MCP Plugin

`litestar-mcp` exposes Litestar route handlers as [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tools and resources over JSON-RPC 2.0.

## Installation

```bash
pip install litestar-mcp
```

## Basic Setup

```python
from litestar import Litestar, get
from litestar_mcp import LitestarMCP, MCPConfig

@get("/users", name="list_users")
async def get_users() -> list[dict]: ...

app = Litestar(
    route_handlers=[get_users],
    plugins=[LitestarMCP(MCPConfig(name="My API"))],
)
```

The MCP endpoint is mounted at `POST /mcp/` by default.

## MCPConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | `str` | `"litestar"` | Server name reported in `initialize` response |
| `base_path` | `str` | `"/mcp"` | URL prefix for the MCP controller |
| `guards` | `list[Guard]` | `[]` | Litestar guards applied to the MCP controller |
| `allowed_origins` | `list[str]` | `["*"]` | CORS origins for the MCP endpoint |
| `auth` | `AuthConfig \| None` | `None` | OAuth 2.1 configuration |
| `include_operations` | `list[str] \| None` | `None` | Whitelist of operation names to expose |
| `exclude_operations` | `list[str] \| None` | `None` | Blacklist of operation names to suppress |
| `include_tags` | `list[str] \| None` | `None` | Only expose routes with these OpenAPI tags |
| `exclude_tags` | `list[str] \| None` | `None` | Suppress routes with these OpenAPI tags |

## Route Discovery

By default, `LitestarMCP` discovers routes from the Litestar OpenAPI schema. Routes are exposed as either **tools** (writable operations) or **resources** (read operations) based on HTTP method:

| HTTP Method | Default MCP Type |
|-------------|-----------------|
| GET | resource |
| POST / PUT / PATCH / DELETE | tool |

Override per route with decorators (see below).

## Marking Routes

### `@mcp_tool`

Explicitly marks a handler as an MCP tool (callable by AI agents):

```python
from litestar import post
from litestar_mcp import mcp_tool

@mcp_tool("create_order")
@post("/orders")
async def create_order(data: OrderCreate) -> Order: ...
```

The string argument sets the MCP tool name. Omit it to use the route's `name` attribute.

### `@mcp_resource`

Explicitly marks a handler as an MCP resource (readable by AI agents):

```python
from litestar import get
from litestar_mcp import mcp_resource

@mcp_resource("orders_list")
@get("/orders", name="list_orders")
async def list_orders() -> list[Order]: ...
```

### Opt Dict (inline metadata)

Pass an `opt` dict in the route handler to control MCP exposure without importing `litestar_mcp`:

```python
@get("/internal/health", opt={"mcp_exclude": True})
async def health_check() -> dict: ...

@post("/orders", opt={"mcp_tool_name": "place_order"})
async def create_order(data: OrderCreate) -> Order: ...
```

Recognized `opt` keys:

| Key | Type | Description |
|-----|------|-------------|
| `mcp_exclude` | `bool` | Exclude this route from MCP entirely |
| `mcp_tool_name` | `str` | Override MCP tool name |
| `mcp_resource_name` | `str` | Override MCP resource name; implies resource type |

## MCPController

`LitestarMCP` registers `MCPController` at `{base_path}/` which handles all JSON-RPC 2.0 requests via `POST`.

### Supported JSON-RPC Methods

| Method | Description |
|--------|-------------|
| `initialize` | Handshake; returns server name, version, capabilities |
| `ping` | Health check; returns `pong` |
| `resources/list` | List all discoverable MCP resources |
| `resources/read` | Read (call) a specific resource by URI |
| `tools/list` | List all discoverable MCP tools |
| `tools/call` | Invoke a tool by name with arguments |

### Example JSON-RPC Call

```json
POST /mcp/
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_order",
    "arguments": {
      "product_id": 42,
      "quantity": 3
    }
  }
}
```

Response:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{ "type": "text", "text": "{\"id\": 99, \"status\": \"pending\"}" }]
  }
}
```

## Built-in OpenAPI Resource

`LitestarMCP` automatically exposes the Litestar OpenAPI schema as an MCP resource:

- **URI**: `openapi://schema`
- **MIME type**: `application/json`
- **Content**: Full OpenAPI 3.x schema from `/schema/openapi.json`

AI agents can read this resource to understand the full API surface before calling tools.

## OAuth 2.1 Authentication

```python
from litestar_mcp import MCPConfig, OAuthConfig

config = MCPConfig(
    name="My Secured API",
    auth=OAuthConfig(
        issuer="https://auth.example.com",
        client_id="mcp-client",
        scopes=["read", "write"],
    ),
)
```

OAuth 2.1 enforces PKCE by default. Token validation uses the issuer's JWKS endpoint.

For simpler cases, use Litestar guards instead:

```python
from litestar_mcp import MCPConfig

config = MCPConfig(
    name="My API",
    guards=[requires_api_key],
)
```

## Filtering Exposed Routes

```python
config = MCPConfig(
    name="Public API",
    # Only expose routes tagged "public"
    include_tags=["public"],
    # Never expose admin operations
    exclude_operations=["admin:delete_user", "admin:list_users"],
)
```

`include_operations` and `exclude_operations` match against route `name` attributes (the string used in Litestar's `name=` parameter).

## Resources vs Tools

| Concept | MCP Type | HTTP Methods | Side Effects |
|---------|----------|-------------|--------------|
| Data retrieval | Resource | GET | None |
| Data mutation | Tool | POST, PUT, PATCH, DELETE | Yes |

Prefer resources for idempotent reads so AI agents can safely call them during reasoning. Tools are for actions with side effects.

## Full Example

```python
from litestar import Litestar, get, post
from litestar_mcp import LitestarMCP, MCPConfig, mcp_tool, mcp_resource

@mcp_resource("product_list")
@get("/products", name="list_products", tags=["public"])
async def list_products() -> list[dict]:
    return [{"id": 1, "name": "Widget"}]

@mcp_tool("add_to_cart")
@post("/cart/items", name="cart:add", tags=["public"])
async def add_to_cart(data: CartItem) -> Cart: ...

@get("/internal/metrics", opt={"mcp_exclude": True})
async def metrics() -> dict: ...

app = Litestar(
    route_handlers=[list_products, add_to_cart, metrics],
    plugins=[LitestarMCP(MCPConfig(
        name="E-Commerce API",
        include_tags=["public"],
    ))],
)
```

## Notes

- `tools/call` arguments are validated against the route's OpenAPI request schema before dispatch.
- Response content is serialized to JSON string and wrapped in MCP `TextContent`.
- `LitestarMCP` does not affect normal HTTP routing — all existing endpoints continue to work unchanged.
- Use `exclude_operations` or `opt={"mcp_exclude": True}` to keep internal/admin routes hidden from MCP clients.
