---
name: claude-api-tool-use
description: "Anthropic SDK 0.40: tool-use loop, messages.stream(), prompt-caching headers, tool_result accumulation, adaptive thinking. Use for backend/app/llm/claude.py. Trigger — EN: anthropic sdk, tool use, streaming, claude-opus-4-8, tool_result, prompt caching, messages.stream, anthropic api. Trigger — UA: anthropic sdk, tool use, стрімінг, claude-opus-4-8, tool_result, кешування промптів, messages.stream, anthropic апі."
---

# Anthropic SDK 0.40 — Tool Use & Streaming

Reference for `backend/app/llm/claude.py`. SDK version: `anthropic==0.40.*`.

## Model Constant

```python
# llm/claude.py — NEVER hardcode this string outside this module
CLAUDE_MODEL = "claude-opus-4-8"
```

Always use `CLAUDE_MODEL`, never inline `"claude-opus-4-8"` in other files.

## Non-Streaming Tool Use (single complete call)

```python
import anthropic

async def complete(
    self,
    messages: list[dict],
    tools: list[dict],
    system: str,
) -> LLMResponse:
    async with anthropic.AsyncAnthropic(api_key=self._api_key) as client:
        response = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=tools,
        )
    return self._parse_response(response)

def _parse_response(self, response) -> LLMResponse:
    content = []
    for block in response.content:
        if block.type == "text":
            content.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            content.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,  # dict, already parsed by SDK
            })
    return LLMResponse(stop_reason=response.stop_reason, content=content)
```

## Streaming (messages.stream)

Use streaming when the orchestrator yields partial text to the SSE client:

```python
async def stream_complete(
    self,
    messages: list[dict],
    tools: list[dict],
    system: str,
) -> AsyncIterator[dict]:
    async with anthropic.AsyncAnthropic(api_key=self._api_key) as client:
        async with client.messages.stream(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=tools,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        yield {"type": "text_delta", "text": event.delta.text}
                    elif event.delta.type == "input_json_delta":
                        yield {"type": "tool_input_delta", "partial_json": event.delta.partial_json}
                elif event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        yield {
                            "type": "tool_use_start",
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                        }
                elif event.type == "message_stop":
                    final = await stream.get_final_message()
                    yield {"type": "done", "stop_reason": final.stop_reason}
```

Note: `client.messages.stream()` is an async context manager returning an `AsyncMessageStream`. Use `async for event in stream` to get `RawMessageStreamEvent` objects.

## Tool Definitions Format (Anthropic)

```python
tools = [
    {
        "name": "search_catalog",
        "description": "Search the 1C catalog by text query",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    }
]
```

`input_schema` must be a valid JSON Schema object. The SDK validates this at call time.

## Detecting Tool Use in Response

```python
# Non-streaming — check response.stop_reason and response.content
if response.stop_reason == "tool_use":
    tool_blocks = [b for b in response.content if b.type == "tool_use"]
    for block in tool_blocks:
        # block.id — string, use as tool_use_id in tool_result
        # block.name — tool function name
        # block.input — dict of parsed arguments (SDK does JSON parsing)
        await execute_tool(block.name, block.input)
```

## tool_result Accumulation

After executing tools, append them to messages as a `user` turn:

```python
# The assistant turn MUST come first (the tool_use blocks)
messages.append({
    "role": "assistant",
    "content": response.content  # list of content blocks (dicts or SDK objects)
})

# Then the tool results
messages.append({
    "role": "user",
    "content": [
        {
            "type": "tool_result",
            "tool_use_id": block.id,         # must match the tool_use block id
            "content": json.dumps(result),   # MUST be a string, not a dict
        }
        for block, result in zip(tool_blocks, results)
    ]
})
```

**Critical:** `tool_use_id` must exactly match the `id` from the `tool_use` block. Mismatch causes an API error.

## Prompt Caching (optional, subscription)

For long system prompts or tool definitions that repeat across requests:

```python
# Add cache_control to static content blocks
tools_with_cache = [*tools]
tools_with_cache[-1] = {
    **tools_with_cache[-1],
    "cache_control": {"type": "ephemeral"}
}

response = await client.messages.create(
    model=CLAUDE_MODEL,
    system=[
        {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
    ],
    messages=messages,
    tools=tools_with_cache,
    ...
)
```

Note: On Claude subscriptions (Pro/Max), 1-hour prompt cache is automatic. `cache_control` headers opt in to cache specific blocks explicitly. Do NOT add `CLAUDE_CODE_CACHE_TTL` env var — it does not exist.

## Adaptive Thinking

Controlled by `thinking` parameter in SDK 0.40+:

```python
response = await client.messages.create(
    model=CLAUDE_MODEL,
    thinking={"type": "enabled", "budget_tokens": 5000},
    ...
)
```

Control thinking via the `thinking` **API request parameter** directly — `{"type": "enabled", "budget_tokens": 5000}`. There is no working shell environment variable for this on Opus 4.7+.

## Error Handling

```python
from anthropic import APIConnectionError, RateLimitError, APIStatusError

try:
    response = await client.messages.create(...)
except RateLimitError:
    # 429 — exponential backoff
    ...
except APIStatusError as e:
    # 4xx/5xx from Anthropic
    logger.error("Anthropic API error", extra={"status": e.status_code, "body": e.body})
    raise
except APIConnectionError:
    # Network issue
    ...
```

## Testing Pattern (mock the client)

```python
from unittest.mock import AsyncMock, MagicMock

def make_mock_tool_use_response(tool_name: str, tool_input: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.id = "toolu_mock_123"
    block.name = tool_name
    block.input = tool_input

    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [block]
    return response

# In test:
mock_client = AsyncMock()
mock_client.messages.create.return_value = make_mock_tool_use_response(
    "search_catalog", {"query": "test"}
)
```

NEVER call the live Anthropic API in tests. Mock `client.messages.create` or `client.messages.stream`.

## Common Mistakes

- Appending raw SDK objects to `messages` instead of dicts — use `block.model_dump()` or `dict(block)`.
- Using `block.text` on a `tool_use` block — check `block.type` first.
- Passing `content` as string instead of list of blocks to the messages list.
- Using `content[0].text` to get the final answer — there may be multiple text blocks; join them.
- Not serializing `tool.input` result to JSON string before putting in `tool_result.content`.
- Trying to disable adaptive thinking via a shell env var — use the `thinking` API request parameter instead (see Adaptive Thinking section above).

## References

- Anthropic docs: `https://docs.anthropic.com/en/api/messages`
- Tool use guide: `https://docs.anthropic.com/en/docs/build-with-claude/tool-use`
- SDK changelog: `https://github.com/anthropics/anthropic-sdk-python/releases/tag/v0.40.0`

## Trigger phrases (UA)

anthropic sdk, tool use, стрімінг, claude-opus-4-8, tool_result, кешування промптів, messages.stream, anthropic апі, tool_use блок, input_schema, stop_reason, content block, адаптивне мислення.
