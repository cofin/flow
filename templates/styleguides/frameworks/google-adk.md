# Google ADK (Agent Development Kit) Guide

Patterns for building AI agents with Google ADK, SQLSpec, and Litestar.

## Overview

Google ADK provides a framework for building AI agents that can:
- Use tools (functions) to interact with databases and APIs
- Maintain conversation sessions with history
- Stream responses for real-time UI updates

## Core Components

### ADK Runner Setup
```python
from google.adk import Runner
from google.adk.agents import LlmAgent
from google.genai import types
from sqlspec.adapters.asyncpg.adk.store import AsyncpgADKStore
from sqlspec.extensions.adk import SQLSpecSessionService

# Define agent at module level (ADK best practice - reusable across requests)
_agent = LlmAgent(
    name="MyAssistant",
    description="AI assistant for product discovery and support.",
    instruction=BASE_SYSTEM_INSTRUCTION,
    model="gemini-2.0-flash",  # Or settings.vertex_ai.CHAT_MODEL
    tools=ALL_TOOLS,  # List of tool functions
)

class ADKRunner:
    """Main runner for ADK-based assistant system."""

    def __init__(self) -> None:
        """Initialize with SQLSpec session service."""
        store = AsyncpgADKStore(config=db_config)
        self.session_service = SQLSpecSessionService(store)
        self._runner = Runner(
            agent=_agent,
            app_name="my-assistant",
            session_service=self.session_service,
        )

    async def process_request(
        self,
        query: str,
        user_id: str = "default",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Process user request through the ADK agent."""
        session = await self._ensure_session(user_id, session_id)

        content = types.Content(
            role="user",
            parts=[types.Part(text=query)],
        )

        events = self._runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        )

        return await self._process_events(events)

    async def _ensure_session(self, user_id: str, session_id: str | None) -> Session:
        """Get or create session."""
        if session_id:
            existing = await self.session_service.get_session(
                app_name="my-assistant",
                user_id=user_id,
                session_id=session_id,
            )
            if existing:
                return existing

        return await self.session_service.create_session(
            app_name="my-assistant",
            user_id=user_id,
            session_id=session_id,
            state={},
        )
```

## Tool Functions

### Tool Pattern with Dishka DI
```python
from dishka import AsyncContainer

# Global container reference (set during app startup)
_app_container: AsyncContainer | None = None

def set_app_container(container: AsyncContainer) -> None:
    """Set the application container for ADK tools."""
    global _app_container
    _app_container = container

def get_app_container() -> AsyncContainer:
    """Get the application container."""
    if _app_container is None:
        raise RuntimeError("Container not set. Call set_app_container() at startup.")
    return _app_container

async def search_products(
    query: str,
    limit: int = 5,
    similarity_threshold: float = 0.7,
) -> dict[str, Any]:
    """Search products using vector similarity.

    ADK calls this function with parameters from the LLM.
    We create a request-scoped container for DI.
    """
    container = get_app_container()
    async with container() as request_container:
        tools_service = await request_container.get(AgentToolsService)
        return await tools_service.search_products(query, limit, similarity_threshold)

async def get_product_details(product_id: str) -> dict[str, Any]:
    """Get product details by ID."""
    container = get_app_container()
    async with container() as request_container:
        tools_service = await request_container.get(AgentToolsService)
        return await tools_service.get_product_details(product_id)

async def classify_intent(query: str) -> dict[str, Any]:
    """Classify user intent using vector similarity."""
    container = get_app_container()
    async with container() as request_container:
        tools_service = await request_container.get(AgentToolsService)
        return await tools_service.classify_intent(query)

# Export all tools for agent registration
ALL_TOOLS = [
    search_products,
    get_product_details,
    classify_intent,
]
```

### Tool Service (Business Logic)
```python
class AgentToolsService(SQLSpecService):
    """Service containing agent tool business logic."""

    def __init__(
        self,
        driver: AsyncDriverAdapterBase,
        product_service: ProductService,
        vertex_ai_service: VertexAIService,
        intent_service: IntentService,
    ) -> None:
        super().__init__(driver)
        self.product_service = product_service
        self.vertex_ai_service = vertex_ai_service
        self.intent_service = intent_service

    async def search_products(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Search products with vector similarity."""
        import time
        start_time = time.time()

        # Get embedding (with cache check)
        embedding_start = time.time()
        query_embedding, cache_hit = await self.vertex_ai_service.get_text_embedding(
            query, return_cache_status=True
        )
        embedding_ms = (time.time() - embedding_start) * 1000

        # Vector search
        db_start = time.time()
        products = await self.product_service.search_by_vector(
            query_embedding=query_embedding,
            similarity_threshold=similarity_threshold,
            limit=limit,
        )
        db_ms = (time.time() - db_start) * 1000

        return {
            "products": [
                {
                    "id": str(p["id"]),
                    "name": p["name"],
                    "description": p["description"],
                    "price": float(p["current_price"]),
                    "similarity_score": float(p["similarity_score"]),
                }
                for p in products
            ],
            "timing": {
                "total_ms": (time.time() - start_time) * 1000,
                "embedding_ms": embedding_ms,
                "db_ms": db_ms,
            },
            "embedding_cache_hit": cache_hit,
            "results_count": len(products),
        }

    async def classify_intent(self, query: str) -> dict[str, Any]:
        """Classify user intent via vector similarity to exemplars."""
        result = await self.intent_service.classify_intent(query)
        return {
            "intent": result.intent,
            "confidence": float(result.confidence),
            "exemplar_phrase": result.exemplar_phrase,
            "embedding_cache_hit": result.embedding_cache_hit,
        }
```

## Vertex AI Service

### Embeddings and Chat
```python
from google import genai

class VertexAIService:
    """Vertex AI service for embeddings and chat."""

    def __init__(self, cache_service: CacheService | None = None) -> None:
        self.settings = get_settings()
        self._cache_service = cache_service

        # Initialize client (supports both Vertex AI and Google AI API)
        if self.settings.vertex_ai.PROJECT_ID:
            # Vertex AI (uses ADC or GOOGLE_APPLICATION_CREDENTIALS)
            self._client = genai.Client()
        elif self.settings.vertex_ai.API_KEY:
            # Google AI API (uses API key)
            self._client = genai.Client(api_key=self.settings.vertex_ai.API_KEY)
        else:
            self._client = None

    async def get_text_embedding(
        self,
        text: str,
        model: str | None = None,
        *,
        return_cache_status: bool = False,
    ) -> list[float] | tuple[list[float], bool]:
        """Generate text embedding with optional caching."""
        model_name = model or self.settings.vertex_ai.EMBEDDING_MODEL
        cache_hit = False

        # Check cache first
        if self._cache_service and self.settings.cache.EMBEDDING_CACHE_ENABLED:
            cached = await self._cache_service.get_cached_embedding(text, model_name)
            if cached:
                if return_cache_status:
                    return cached.embedding, True
                return cached.embedding

        # Generate embedding
        response = await self._client.aio.models.embed_content(
            model=model_name,
            contents=text,
        )
        embedding = list(response.embeddings[0].values)

        # Cache result
        if self._cache_service and self.settings.cache.EMBEDDING_CACHE_ENABLED:
            await self._cache_service.set_cached_embedding(text, embedding, model_name)

        if return_cache_status:
            return embedding, cache_hit
        return embedding

    async def generate_chat_response_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming chat response."""
        model_name = model or self.settings.vertex_ai.CHAT_MODEL

        # Convert to Google format
        formatted = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in messages
        ]

        async for chunk in await self._client.aio.models.generate_content_stream(
            model=model_name,
            contents=formatted,
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
            ),
        ):
            if chunk.candidates:
                for part in chunk.candidates[0].content.parts:
                    if part.text:
                        yield part.text
```

## Dishka Providers

### Provider Setup
```python
from dishka import AsyncContainer, Provider, Scope, provide
from sqlspec.adapters.asyncpg import AsyncpgConfig
from sqlspec.base import SQLSpec
from sqlspec.driver import AsyncDriverAdapterBase

class SQLSpecProvider(Provider):
    """Database infrastructure provider."""

    @provide(scope=Scope.APP)
    def get_sqlspec_manager(self) -> SQLSpec:
        return db_manager

    @provide(scope=Scope.APP)
    def get_database_config(self) -> AsyncpgConfig:
        return db_config

    @provide(scope=Scope.REQUEST)
    async def get_db_session(
        self,
        manager: SQLSpec,
        config: AsyncpgConfig,
    ) -> AsyncIterable[AsyncDriverAdapterBase]:
        async with manager.provide_session(config) as session:
            yield session

class CoreServiceProvider(Provider):
    """Business services provider."""

    scope = Scope.REQUEST

    @provide
    def get_product_service(self, driver: AsyncDriverAdapterBase) -> ProductService:
        return ProductService(driver)

    @provide
    def get_cache_service(self, driver: AsyncDriverAdapterBase) -> CacheService:
        return CacheService(driver)

    @provide
    def get_vertex_ai_service(self, cache_service: CacheService) -> VertexAIService:
        return VertexAIService(cache_service=cache_service)

    @provide
    def get_agent_tools_service(
        self,
        driver: AsyncDriverAdapterBase,
        product_service: ProductService,
        vertex_ai_service: VertexAIService,
        intent_service: IntentService,
    ) -> AgentToolsService:
        return AgentToolsService(
            driver=driver,
            product_service=product_service,
            vertex_ai_service=vertex_ai_service,
            intent_service=intent_service,
        )

class ADKProvider(Provider):
    """ADK-specific provider."""

    @provide(scope=Scope.APP)
    def get_adk_runner(self) -> ADKRunner:
        """ADKRunner as singleton (stateless, reusable)."""
        return ADKRunner()
```

## Streaming Responses

### Event Processing
```python
async def stream_request(
    self,
    query: str,
    user_id: str,
    session_id: str | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Stream ADK events for real-time UI."""
    session = await self._ensure_session(user_id, session_id)

    content = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )

    events = self._runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=content,
    )

    async for event in events:
        # Stream text progressively
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    yield {"type": "text", "text": part.text}

        # Stream function results
        if hasattr(event, "get_function_responses"):
            for func_response in event.get_function_responses():
                if func_response.name == "search_products":
                    yield {
                        "type": "products",
                        "data": func_response.response,
                    }
```

## Application Startup

### Litestar Integration
```python
from litestar import Litestar
from dishka import make_async_container
from dishka.integrations.litestar import setup_dishka
from app.services._adk.tools import set_app_container

def create_app() -> Litestar:
    container = make_async_container(
        SQLSpecProvider(),
        CoreServiceProvider(),
        ADKProvider(),
        skip_validation=True,
    )

    # Make container available to ADK tools
    set_app_container(container)

    app = Litestar(route_handlers=[...])
    setup_dishka(container, app)
    return app
```

## Best Practices

- Define agents at module level (singleton pattern)
- Use `SQLSpecSessionService` for persistent conversation history
- Create request-scoped containers in tool functions
- Cache embeddings in database for performance
- Return structured dicts from tools (not raw objects)
- Include timing metrics for observability
- Filter internal tool-calling messages from final response

## Anti-Patterns

```python
# Bad: Creating new agent per request
async def handle_request(query: str):
    agent = LlmAgent(...)  # Expensive, wasteful
    runner = Runner(agent=agent, ...)

# Good: Reuse singleton agent
_agent = LlmAgent(...)  # Module level
runner = Runner(agent=_agent, ...)

# Bad: No DI in tool functions
async def search_products(query: str):
    service = ProductService(get_driver())  # Manual wiring

# Good: Use container for DI
async def search_products(query: str):
    async with container() as request_container:
        service = await request_container.get(AgentToolsService)

# Bad: Returning ORM objects from tools
async def get_product(id: str):
    return await service.get(id)  # ORM object can't serialize

# Good: Return plain dicts
async def get_product(id: str):
    product = await service.get(id)
    return {"id": str(product.id), "name": product.name, ...}
```
