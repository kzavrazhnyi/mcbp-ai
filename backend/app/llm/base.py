"""Контракт LLM-провайдера + типи кроку tool-calling.

Історія діалогу передається у провайдер-нативному форматі (`messages: list[dict]`),
а кожен провайдер сам конвертує її у формат свого API. Спільний цикл
(`app.services.ai_orchestrator`) працює через цей інтерфейс для всіх провайдерів.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class ToolInvocation:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMStep:
    """Результат одного ходу моделі."""

    text: str = ""
    tool_calls: list[ToolInvocation] = field(default_factory=list)
    raw: Any = None  # нативний об'єкт відповіді — для коректного round-trip у діалог

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


@runtime_checkable
class LLMProvider(Protocol):
    async def step(
        self, system: str, messages: list[dict[str, Any]], tools: list[ToolDef]
    ) -> LLMStep:
        ...

    def assistant_message(self, step: LLMStep) -> dict[str, Any]:
        ...

    def tool_result_message(self, call: ToolInvocation, result: Any) -> dict[str, Any]:
        ...
