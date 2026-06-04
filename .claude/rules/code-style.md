# Code Style — mcbp-ai (Python / FastAPI)

Enforced by Ruff. No mypy (project has none — do NOT add mypy-strict posture).

## Python Version & Import Header

- Target: **Python 3.11+**
- Every module begins with: `from __future__ import annotations`
- Ruff config: `line-length = 100`, `target-version = "py311"`

## Formatting

- **Indent:** 4 spaces. No tabs.
- **Line endings:** LF (Unix-style), even on Windows (git should handle CRLF conversion).
- **Line length:** 100 characters (Ruff E501).
- **Trailing commas:** always on multiline literals and function signatures.
- **Blank lines:** 2 between top-level definitions; 1 inside a class.

## Type Annotations

- **Full type hints on all public functions and methods** — parameters AND return types.
- Use `X | None` (PEP 604 union syntax), NOT `Optional[X]`.
- Use `list[X]`, `dict[K, V]`, `tuple[X, ...]` (lowercase generics, PEP 585).
- Pydantic model fields: always annotate with the concrete type.
- **NO `Any` usage** unless in a respx mock fixture where the type is truly opaque.

## Imports

```python
from __future__ import annotations

# stdlib
import asyncio
from typing import TYPE_CHECKING

# third-party
import httpx
from fastapi import APIRouter
from pydantic import BaseModel

# local — absolute package imports
from app.core.config import Settings
from app.clients.mcbp import McbpClient
```

Order: stdlib → third-party → local. `isort`-compatible (Ruff handles this).

- **No wildcard imports** (`from x import *`).
- **Lazy imports for optional providers:** `import openai` inside function body to avoid import error when OpenAI is not configured.

```python
async def _call_openai(prompt: str, settings: Settings) -> str:
    import openai  # lazy — avoids ImportError if openai not installed
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    ...
```

## Naming

| Kind | Convention | Example |
|---|---|---|
| Module | `snake_case` | `ai_orchestrator.py` |
| Class | `PascalCase` | `McbpClient`, `ChatRequest` |
| Function / method | `snake_case` | `search_catalog`, `get_register_balance` |
| Constant | `UPPER_SNAKE` | `DEFAULT_TIMEOUT`, `CLAUDE_MODEL` |
| Private helper | `_snake_case` | `_build_tool_result` |
| Pydantic field | `snake_case` | `session_id`, `query_text` |

## Async Rules

- **All I/O is async.** No `requests`, no `httpx.Client` (sync) — use `httpx.AsyncClient`.
- **Never block the event loop.** CPU-heavy tasks → `asyncio.to_thread(...)`.
- **Always `await`** coroutines; never fire-and-forget unless the pattern explicitly requires it.
- **httpx session pooling:** create `AsyncClient` once per lifespan; do NOT create per-request.

## FastAPI Conventions

- Router files live in `backend/app/routers/<name>.py`.
- Use `APIRouter(prefix="/...", tags=["..."])`.
- Pydantic models for request/response bodies — never raw dicts at route level.
- Dependency injection for settings + clients (via `Depends`).
- SSE endpoint: use `StreamingResponse` with `media_type="text/event-stream"`.

## Pydantic v2 Rules

- Models inherit from `pydantic.BaseModel`.
- Use `model_validate(data)` NOT `.parse_obj(data)` (v1 API).
- Use `model_dump()` NOT `.dict()`.
- Field aliases only when the JSON key differs from the Python identifier.

## Ruff Configuration (pyproject.toml)

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]   # handled by formatter

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

## ❌ DO NOT

- Add mypy or type: ignore comments (project has no mypy setup).
- Use synchronous HTTP clients.
- Hardcode API keys or passwords anywhere.
- Import `openai` at module level (lazy import only).
- Use `print()` for debug output — use `logging.getLogger(__name__)`.
- Catch bare `except Exception` without re-raising or logging with context.

## Trigger phrases (UA)

стиль коду, code style, форматування, ruff, pep8, type hints, анотації типів, async, імпорти, fastapi конвенції, pydantic v2.
