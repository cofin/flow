# Domain Auto-Discovery Plugin & CLI

## Domain Auto-Discovery Plugin

The `DomainPlugin` automatically discovers controllers from domain packages:

```python
from litestar_vite.plugin import DomainPlugin, DomainPluginConfig

domain = DomainPlugin(DomainPluginConfig(
    domain_packages=["myapp.domain"],
    discover_controllers=True,  # Find in */controllers/
    discover_jobs=True,         # Find @task decorators in */jobs/
    use_dishka_router=True,     # Wrap in LitestarRouter for DI
))

# Controllers are auto-discovered from:
# myapp/domain/*/controllers/*.py
# myapp/domain/*/routes/*.py
```

## CLI with Async Injection

See the `dishka` skill for the full `@async_inject` pattern.

```python
import rich_click as click

@users_group.command(name="create")
@click.option("--email", "-e", required=True)
@async_inject  # See dishka skill for implementation
async def create_user(
    user_service: UserService,  # Injected by Dishka
    email: str,                 # From Click option
) -> None:
    user = await user_service.create_by_email(email)
    console.print(f"Created user: {user.id}")
```
