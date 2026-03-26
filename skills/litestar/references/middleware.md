# Middleware

```python
from litestar.middleware import AbstractMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send
from litestar.enums import ScopeType

class TimingMiddleware(AbstractMiddleware):
    scopes = {ScopeType.HTTP}
    exclude = ["health", "metrics"]

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send
    ) -> None:
        start = time.perf_counter()
        await self.app(scope, receive, send)
        duration = time.perf_counter() - start
        logger.info(f"Request took {duration:.3f}s")
```
