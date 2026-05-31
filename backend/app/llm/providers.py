"""Concrete LLM providers. Selected at runtime via MCBP_LLM_PROVIDER.

Anthropic uses prompt caching (system + tools prefix) and adaptive thinking on
Opus 4.8. SDK-и імпортуються ліниво — щоб mock/тести працювали без них.
"""
from __future__ import annotations

import json
from typing import Any

from app.core.config import Settings
from app.llm.base import LLMProvider, LLMStep, ToolDef, ToolInvocation


# ---------------- Anthropic ----------------
class AnthropicProvider:
    def __init__(self, settings: Settings):
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    def _tools(self, tools: list[ToolDef]) -> list[dict]:
        api = [
            {"name": t.name, "description": t.description, "input_schema": t.parameters}
            for t in tools
        ]
        if api:  # кешуємо статичний префікс (system + tools)
            api[-1] = {**api[-1], "cache_control": {"type": "ephemeral"}}
        return api

    async def step(self, system, messages, tools) -> LLMStep:
        resp = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            tools=self._tools(tools) if tools else [],
        )
        text_parts, calls = [], []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                calls.append(ToolInvocation(id=block.id, name=block.name, arguments=dict(block.input or {})))
        return LLMStep(text="".join(text_parts), tool_calls=calls, raw=resp.content)

    def assistant_message(self, step: LLMStep) -> dict:
        return {"role": "assistant", "content": step.raw}

    def tool_result_message(self, call: ToolInvocation, result: Any) -> dict:
        return {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            }],
        }


# ---------------- OpenAI ----------------
class OpenAIProvider:
    def __init__(self, settings: Settings):
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    def _tools(self, tools: list[ToolDef]) -> list[dict]:
        return [
            {"type": "function", "function": {
                "name": t.name, "description": t.description, "parameters": t.parameters,
            }}
            for t in tools
        ]

    async def step(self, system, messages, tools) -> LLMStep:
        full = [{"role": "system", "content": system}, *messages]
        resp = await self._client.chat.completions.create(
            model=self._model, messages=full,
            tools=self._tools(tools) if tools else None,
        )
        msg = resp.choices[0].message
        calls = [
            ToolInvocation(id=tc.id, name=tc.function.name,
                           arguments=json.loads(tc.function.arguments or "{}"))
            for tc in (msg.tool_calls or [])
        ]
        return LLMStep(text=msg.content or "", tool_calls=calls, raw=msg)

    def assistant_message(self, step: LLMStep) -> dict:
        m = step.raw
        out: dict[str, Any] = {"role": "assistant", "content": m.content or ""}
        if m.tool_calls:
            out["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in m.tool_calls
            ]
        return out

    def tool_result_message(self, call: ToolInvocation, result: Any) -> dict:
        return {
            "role": "tool",
            "tool_call_id": call.id,
            "content": json.dumps(result, ensure_ascii=False, default=str),
        }


# ---------------- Mock ----------------
class MockProvider:
    """Deterministic two-step loop: first call a tool, then answer.
    Lets the full orchestration path run with no API keys."""
    def __init__(self, settings: Settings):
        self._turn = 0

    async def step(self, system, messages, tools) -> LLMStep:
        self._turn += 1
        if self._turn == 1 and tools:
            t = tools[0]
            args: dict[str, Any] = {}
            req = t.parameters.get("required", [])
            if req:
                args[req[0]] = "Counterparties"
            return LLMStep(tool_calls=[ToolInvocation(id="mock-1", name=t.name, arguments=args)],
                           raw={"role": "assistant", "tool": t.name})
        return LLMStep(text="[mock] Запит оброблено: дані отримано через інструмент і зведено.",
                       raw={"role": "assistant", "content": "mock answer"})

    def assistant_message(self, step: LLMStep) -> dict:
        return {"role": "assistant", "content": step.text or "[tool call]"}

    def tool_result_message(self, call: ToolInvocation, result: Any) -> dict:
        return {"role": "user", "content": f"tool {call.name} -> {json.dumps(result, default=str)[:200]}"}


def build_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(settings)
    if settings.llm_provider == "openai":
        return OpenAIProvider(settings)
    return MockProvider(settings)
