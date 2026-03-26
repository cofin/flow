# Guards (Authentication/Authorization)

```python
from litestar.connection import ASGIConnection
from litestar.handlers import BaseRouteHandler

async def requires_auth(
    connection: ASGIConnection,
    _: BaseRouteHandler,
) -> None:
    """Guard that requires authentication."""
    if not connection.user:
        raise PermissionDeniedException("Authentication required")

# Usage in controller
@get(guards=[requires_auth])
async def protected_route(self) -> dict:
    ...
```
