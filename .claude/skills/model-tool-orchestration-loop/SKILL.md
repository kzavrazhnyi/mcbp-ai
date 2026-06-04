---
name: model-tool-orchestration-loop
description: "The core architecture of mcbp-ai: NL question → LLM provider → tool-call loop → execute against 1C → accumulate results → final answer. Use when working on ai_orchestrator.py, the provider Protocol, SSE fan-out, or designing the messages list format. Trigger — EN: orchestration loop, tool use loop, ai orchestrator, messages list, tool result, sse fan-out, provider protocol, loop until done. Trigger — UA: петля оркестрації, tool use петля, ai orchestrator, список повідомлень, tool result, sse фан-аут, провайдер протокол, цикл до відповіді."
---

# Model-Driven Tool Orchestration Loop

The central architecture of mcbp-ai. The LLM drives the data-fetch loop; the backend is a pure executor.

## Core Invariant

**The backend NEVER decides which tools to call.** Only the LLM decides. The backend:
1. Provides tool definitions (schemas) to the LLM.
2. Detects when the LLM requests a tool call.
3. Executes the tool against 1C.
4. Returns the result to the LLM.
5. Repeats until the LLM produces a final text answer.

## Messages List Format

The orchestrator maintains a `messages` list in the Anthropic/OpenAI format:

```python
messages: list[dict] = [
    {"role": "user", "content": "Який баланс рахунку МутуалСеттлементс на 2024-01-01?"}
]

# After LLM requests a tool:
messages.append({
    "role": "assistant",
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_abc123",
            "name": "get_register_balance",
            "input": {"register_name": "MutualSettlements", "date": "2024-01-01", "dimensions": {}}
        }
    ]
})

# After executing the tool:
messages.append({
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": "toolu_abc123",
            "content": "{\"register\": \"MutualSettlements\", \"balance\": 150000.0, ...}"
        }
    ]
})
```

## Tool Definitions (passed to LLM on every call)

```python
# services/tools.py
TOOL_DEFINITIONS = [
    {
        "name": "search_catalog",
        "description": "Full-text search in the 1C catalog. Use for finding products, counterparties, or any reference items by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search text"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    },
    # ... remaining 5 tools
]
```

## Loop Implementation Pattern

```python
# ai_orchestrator.py
async def run_stream(
    request: ChatRequest,
    settings: AppSettings,
    mcbp_client: McbpClient,
) -> AsyncIterator[str]:
    provider = get_provider(settings)
    tools_executor = ToolsExecutor(mcbp_client)
    messages = [{"role": "user", "content": request.query}]

    MAX_ITERATIONS = 10  # safety cap — prevent infinite loops
    for iteration in range(MAX_ITERATIONS):
        response = await provider.complete(
            messages=messages,
            tools=TOOL_DEFINITIONS,
            system=SYSTEM_PROMPT,
        )

        if response.stop_reason == "tool_use":
            tool_calls = [b for b in response.content if b["type"] == "tool_use"]
            tool_results = []

            for tc in tool_calls:
                yield f"data: {json.dumps({'type': 'tool_call', 'name': tc['name']})}\n\n"
                result = await tools_executor.execute(tc["name"], tc["input"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": json.dumps(result),
                })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            text = "".join(
                b["text"] for b in response.content
                if b.get("type") == "text"
            )
            yield f"data: {json.dumps({'type': 'delta', 'text': text})}\n\n"
            yield 'data: {"type": "done"}\n\n'
            return

        else:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Unexpected stop_reason: {response.stop_reason}'})}\n\n"
            return

    # Safety cap reached
    yield 'data: {"type": "error", "message": "Max iterations reached"}\n\n'
```

## Provider Protocol

```python
# llm/protocol.py
from typing import Protocol, Any

class LLMResponse:
    stop_reason: str  # "tool_use" | "end_turn" | "max_tokens"
    content: list[dict[str, Any]]

class LLMProvider(Protocol):
    async def complete(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str,
    ) -> LLMResponse: ...
```

The orchestrator only uses `LLMProvider`. Provider-specific parsing happens inside `claude.py` / `openai.py`.

## SSE Event Types

| Event | JSON payload | When |
|---|---|---|
| `tool_call` | `{"type": "tool_call", "name": "search_catalog"}` | Tool invoked (before result) |
| `delta` | `{"type": "delta", "text": "Баланс складає..."}` | Final text chunk |
| `done` | `{"type": "done"}` | Stream complete |
| `error` | `{"type": "error", "message": "..."}` | Any error, then close |

## System Prompt Pattern

```python
SYSTEM_PROMPT = """You are an AI assistant for the MCBP+ ERP system.
You have access to tools that query the 1C BAS MCBP+ database.
Use tools to fetch data needed to answer the user's question.
Always use Ukrainian for the final answer unless the user explicitly asks otherwise.
Do not guess data — if you need a value, use a tool to fetch it.
"""
```

## Safety Caps

- `MAX_ITERATIONS = 10` — prevents infinite loops if the model keeps requesting tools.
- `MAX_TOKENS = 4096` per LLM call — prevents runaway cost.
- `TIMEOUT = 30s` per 1C HTTP call — surfaces slow 1C response as an error.

## Testing the Loop

Always mock the provider in tests. A mock that simulates one tool call then `end_turn`:

```python
class MockProvider:
    def __init__(self, tool_name: str, tool_input: dict, final_text: str):
        self._calls = 0
        self._tool_name = tool_name
        self._tool_input = tool_input
        self._final_text = final_text

    async def complete(self, messages, tools, system):
        self._calls += 1
        if self._calls == 1:
            return LLMResponse(
                stop_reason="tool_use",
                content=[{"type": "tool_use", "id": "mock-id", "name": self._tool_name, "input": self._tool_input}]
            )
        return LLMResponse(
            stop_reason="end_turn",
            content=[{"type": "text", "text": self._final_text}]
        )
```

## Common Mistakes

- Forgetting to append `{"role": "assistant", "content": response.content}` before tool results — Anthropic API requires the assistant turn before the user's tool_result turn.
- Not serializing tool results to JSON string — the `content` field in `tool_result` must be a string, not a dict.
- No `MAX_ITERATIONS` safety cap — a buggy model can loop indefinitely.
- Swallowing exceptions in the async generator — must yield an error event and return.
- Sharing state across requests — the `messages` list must be fresh per request, never a module-level variable.

## Trigger phrases (UA)

петля оркестрації, tool use петля, ai orchestrator, список повідомлень, tool result, sse фан-аут, провайдер протокол, цикл до відповіді, MAX_ITERATIONS, stop_reason, tool_use блок.
