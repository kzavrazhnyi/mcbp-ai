"""AI orchestrator: runs the model→tool→model loop.

The model is given the MCBP_AI tools and decides which to call. We execute each
call against 1C, feed results back, and repeat until the model produces a final
answer or we hit the iteration cap. This is the 'model-driven data flow' core.
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from app.clients.mcbp import MCBPClient
from app.core.config import Settings
from app.core.errors import MCBPError
from app.llm.base import LLMProvider
from app.services.tools import TOOLS, tool_defs

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ти — асистент над даними системи MCBP+ (1С). "
    "Ти НЕ маєш даних безпосередньо — отримуй їх лише через надані інструменти. "
    "Плануй послідовність викликів: спершу знайди потрібні довідкові елементи (ref), "
    "потім тягни документи/залишки. Відповідай українською, стисло, з конкретними числами. "
    "Якщо інструмент повертає помилку доступу — поясни її користувачу, не вигадуй дані."
)


class Orchestrator:
    def __init__(self, settings: Settings, mcbp: MCBPClient, llm: LLMProvider):
        self._s = settings
        self._mcbp = mcbp
        self._llm = llm

    async def _execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = TOOLS.get(name)
        if not tool:
            return {"error": f"unknown tool: {name}"}
        try:
            return await tool.executor(self._mcbp, arguments)
        except MCBPError as e:
            return {"error": {"code": e.code, "message": e.message}}
        except (KeyError, TypeError) as e:
            return {"error": {"code": "BAD_ARGUMENTS",
                              "message": f"Tool {name} missing/invalid argument: {e}"}}

    async def run(self, message: str, allowed_tools: list[str] | None = None) -> dict:
        """Non-streaming: returns final answer + the tool calls that were made."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": message}]
        defs = tool_defs(allowed_tools)
        made: list[dict] = []

        for _ in range(self._s.llm_max_tool_iterations):
            step = await self._llm.step(SYSTEM_PROMPT, messages, defs)
            messages.append(self._llm.assistant_message(step))

            if not step.wants_tools:
                return {"answer": step.text, "tool_calls": made}

            for call in step.tool_calls:
                result = await self._execute_tool(call.name, call.arguments)
                made.append({"name": call.name, "arguments": call.arguments})
                messages.append(self._llm.tool_result_message(call, result))

        return {"answer": "Перевищено ліміт кроків обробки.", "tool_calls": made}

    async def stream(self, message: str, allowed_tools: list[str] | None = None) -> AsyncIterator[dict]:
        """Streaming variant: yields SSE-friendly events (tool steps + final)."""
        messages: list[dict[str, Any]] = [{"role": "user", "content": message}]
        defs = tool_defs(allowed_tools)

        for _ in range(self._s.llm_max_tool_iterations):
            step = await self._llm.step(SYSTEM_PROMPT, messages, defs)
            messages.append(self._llm.assistant_message(step))

            if not step.wants_tools:
                yield {"type": "answer", "text": step.text}
                return

            for call in step.tool_calls:
                yield {"type": "tool_call", "name": call.name, "arguments": call.arguments}
                result = await self._execute_tool(call.name, call.arguments)
                yield {"type": "tool_result", "name": call.name, "ok": "error" not in (result or {})}
                messages.append(self._llm.tool_result_message(call, result))

        yield {"type": "answer", "text": "Перевищено ліміт кроків обробки."}
