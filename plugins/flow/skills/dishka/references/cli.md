# CLI Integration

## Click with Async Injection

```python
import functools
from collections.abc import Callable, Coroutine
from typing import Any, ParamSpec, TypeVar

import anyio
from dishka import AsyncContainer

P = ParamSpec("P")
R = TypeVar("R")

def async_inject(
    func: Callable[P, Coroutine[Any, Any, R]],
) -> Callable[..., R]:
    """Decorator for Click commands with Dishka injection."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> R:
        async def run() -> R:
            container = make_cli_container()
            async with container() as request_container:
                # Resolve dependencies from type hints
                resolved = {}
                for name, hint in func.__annotations__.items():
                    if name == "return":
                        continue
                    if name not in kwargs or kwargs[name] is None:
                        try:
                            resolved[name] = await request_container.get(hint)
                        except Exception:
                            pass  # Not a DI type, skip
                return await func(*args, **{**kwargs, **resolved})
        return anyio.from_thread.run(run)

    return wrapper

# Usage
@click.command()
@click.option("--email", "-e", required=True)
@async_inject
async def create_user(
    user_service: UserService,  # Injected by Dishka
    email: str,                 # From Click option
) -> None:
    user = await user_service.create(email=email)
    print(f"Created: {user.id}")
```
