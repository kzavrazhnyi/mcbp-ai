# Architecture — mcbp-ai

## Package Structure

```
backend/app/
  core/          — AppSettings (pydantic-settings), logging config, lifespan
  clients/       — McbpClient (httpx async pool to 1C), MockMcbpClient
  llm/           — provider Protocol, claude.py, openai.py, factory.py
  services/      — tools.py (tool registry), ai_orchestrator.py
  routers/       — chat.py (SSE endpoint), health.py
```

Each package has one clear responsibility. No cross-cutting imports upward (routers → services → clients, NOT clients → routers).

## Dependency Direction (layered)

```
routers → services → clients
       ↘           ↗
         llm/
```

- `routers` call `services` (orchestrator, tool executor).
- `services/ai_orchestrator.py` calls `llm/` (provider) and `services/tools.py` (tool runner).
- `services/tools.py` calls `clients/mcbp.py` for each data-fetch tool.
- `clients/mcbp.py` talks to 1C MCBP_AI HTTP service.
- **llm/** does NOT import from clients directly — the orchestrator mediates.

## Model-Driven Flow (no hardcoded query logic)

```
POST /chat  (or GET /chat/stream for SSE)
  │
  ▼
ai_orchestrator.py
  │  1. Build system prompt + user message
  │  2. Call LLM provider with tool definitions
  │  3. If model returns tool_use → execute tools
  │     ├── search_catalog → clients.mcbp.search_catalog(...)
  │     ├── get_documents  → clients.mcbp.get_documents(...)
  │     ├── get_register_balance → clients.mcbp.get_register_balance(...)
  │     ├── filter_catalog → clients.mcbp.filter_catalog(...)
  │     ├── list_metadata  → clients.mcbp.list_metadata(...)
  │     └── describe_metadata → clients.mcbp.describe_metadata(...)
  │  4. Append tool results, loop back to step 2
  │  5. Until model returns final text → yield via SSE
```

**Critical invariant:** the LLM decides WHICH tools to call and in WHAT ORDER. The backend never picks tools based on keywords in the user message.

## Provider Abstraction (Protocol + lazy imports)

```python
# llm/protocol.py
from typing import Protocol, AsyncIterator

class LLMProvider(Protocol):
    async def stream_tool_use(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str,
    ) -> AsyncIterator[dict]: ...
```

- `llm/claude.py` — implements `LLMProvider` using `anthropic.AsyncAnthropic`.
- `llm/openai.py` — implements `LLMProvider` using `openai.AsyncOpenAI` (lazy import).
- `llm/factory.py` — `get_provider(settings) -> LLMProvider` factory.

The orchestrator only knows `LLMProvider`. Switching providers = changing a settings value.

## Mock vs Side-Effecting Separation

| Class | Talks to | When used |
|---|---|---|
| `McbpClient` | Real 1C MCBP_AI HTTP service | Production |
| `MockMcbpClient` | In-memory fixtures | Tests + offline dev |

Both implement the same interface. The factory in `core/` selects based on `settings.mock_mode`.

**Tests MUST use `MockMcbpClient` or `respx`.** No live 1C calls in `backend/tests/`.

## httpx Session Lifecycle

```python
# core/lifespan.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(base_url=settings.mcbp_base_url, ...) as client:
        app.state.mcbp_client = McbpClient(client)
        yield
```

One `AsyncClient` instance per application lifetime. Do NOT create per-request.

## SSE (Server-Sent Events)

The `/chat/stream` route returns a `StreamingResponse` with `media_type="text/event-stream"`.

```python
async def event_generator():
    async for chunk in orchestrator.run_stream(request, settings):
        yield f"data: {chunk}\n\n"

return StreamingResponse(event_generator(), media_type="text/event-stream")
```

Fan-out to multiple event types: `delta` (partial text), `tool_call` (tool invoked), `done` (final).

## Settings (pydantic-settings)

```python
class AppSettings(BaseSettings):
    anthropic_api_key: str
    openai_api_key: str | None = None
    mcbp_base_url: str
    mcbp_onec_user: str
    mcbp_onec_password: str
    mock_mode: bool = False
    llm_provider: str = "claude"  # "claude" | "openai"
    model_config = SettingsConfigDict(env_file="backend/.env")
```

## Hard Architecture Rules

- **No ORM.** No Django. No SQLAlchemy. The data store is 1C MCBP_AI over HTTP.
- **No hardcoded tool routing.** All tool dispatch goes through the tool registry in `services/tools.py`.
- **No `print()`.** All logging via `logging.getLogger(__name__)` with structured fields.
- **Pydantic validation at every boundary.** API request bodies, API responses from 1C, LLM tool inputs — all validated via Pydantic models.

## Trigger phrases (UA)

архітектура, пакети, структура, шари, dependency injection, провайдер, protocol, model-driven, tool loop, sse, lifespan, mock, mcbp клієнт.
