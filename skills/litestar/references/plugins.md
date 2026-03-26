# Plugin Development

```python
from litestar.plugins import InitPluginProtocol
from litestar.config.app import AppConfig
from dataclasses import dataclass

@dataclass
class MyPluginConfig:
    enabled: bool = True
    api_key: str | None = None

class MyPlugin(InitPluginProtocol):
    __slots__ = ("config",)

    def __init__(self, config: MyPluginConfig | None = None) -> None:
        self.config = config or MyPluginConfig()

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Modify app config during initialization."""
        if self.config.enabled:
            app_config.state["my_plugin"] = self
            # Add routes, middleware, etc.
        return app_config
```
