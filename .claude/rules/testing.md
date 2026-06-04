# Testing — mcbp-ai

pytest + pytest-asyncio + respx. Manual runs only (no CI). 7 smoke tests as the baseline.

## Stack

| Tool | Purpose |
|---|---|
| pytest 8.3 | Test runner |
| pytest-asyncio | Async test support (`asyncio_mode=auto`) |
| respx | httpx mock (intercept `AsyncClient` calls without side effects) |
| `MockMcbpClient` | In-memory mock for 1C responses |

**NO mypy.** Do not add `--strict` or type-check in test runs.

## Configuration (pyproject.toml)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["backend/tests"]
```

With `asyncio_mode=auto`, all `async def test_*` functions run automatically as async tests without needing `@pytest.mark.asyncio`.

## Test Layout

```
backend/tests/
  conftest.py            — shared fixtures (mock client, app, settings)
  test_mcbp_client.py    — unit tests for McbpClient with respx
  test_tools.py          — tool registry dispatch tests
  test_orchestrator.py   — ai_orchestrator.py with mocked provider
  test_routers.py        — FastAPI routes via httpx.AsyncClient (TestClient)
```

## Pure Mock Mode Rule

**No live HTTP calls in tests.** Every external call is mocked:
- `McbpClient` calls → mock via `respx` or `MockMcbpClient`.
- LLM provider calls → mock with fixture returning structured tool_use/text responses.

Reason: tests must run offline, deterministically, without 1C credentials.

## Fixtures Pattern

```python
# conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_app
from app.core.config import AppSettings

@pytest.fixture
def mock_settings() -> AppSettings:
    return AppSettings(
        anthropic_api_key="test-key",
        mcbp_base_url="http://mock-1c",
        mcbp_onec_user="test",
        mcbp_onec_password="test",
        mock_mode=True,
    )

@pytest.fixture
async def client(mock_settings) -> AsyncClient:
    app = create_app(mock_settings)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
```

## respx Pattern (for McbpClient unit tests)

```python
import respx
import httpx

@respx.mock
async def test_search_catalog():
    respx.post("http://mock-1c/catalog/search").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    client = McbpClient(httpx.AsyncClient(base_url="http://mock-1c"))
    result = await client.search_catalog(query="test")
    assert result.items == []
```

## 7 Smoke Tests (baseline)

The project targets at minimum these 7 tests:

1. `test_health_endpoint` — GET /health returns 200
2. `test_search_catalog_tool` — tool executes against mock, returns typed result
3. `test_get_documents_tool` — tool executes against mock, returns typed result
4. `test_get_register_balance_tool` — tool executes, returns balance model
5. `test_orchestrator_single_tool_call` — orchestrator calls one tool, returns final answer
6. `test_orchestrator_multi_turn` — orchestrator loops tool → result → text
7. `test_chat_stream_endpoint` — SSE endpoint yields at least one `data:` event

## Running Tests

```powershell
# from project root on Windows
python -m pytest backend/tests/ -v

# single file
python -m pytest backend/tests/test_mcbp_client.py -v

# specific test
python -m pytest backend/tests/test_orchestrator.py::test_orchestrator_single_tool_call -v
```

## ❌ DO NOT

- Use `@pytest.mark.asyncio` decorators — `asyncio_mode=auto` handles it.
- Call live 1C API in any test — always use mock/respx.
- Call live Anthropic/OpenAI API in any test — always mock the provider.
- Import `openai` at module level in test files — use lazy fixture.
- Skip verification — run the tests and confirm they pass before reporting done.

## Trigger phrases (UA)

тести, pytest, asyncio тести, respx, mock, фікстури, smoke tests, запустити тести, без CI, asyncio_mode auto.
