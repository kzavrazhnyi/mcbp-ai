"""Контейнер залежностей: один екземпляр MCBPClient + LLM-провайдера + оркестратора
на весь застосунок. Створюється на startup, закривається на shutdown.
"""

from __future__ import annotations

from app.clients.mcbp import MCBPClient
from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.providers import build_provider
from app.services.ai_orchestrator import Orchestrator


class Container:
    def __init__(self) -> None:
        self.settings: Settings = get_settings()
        self.mcbp: MCBPClient | None = None
        self.llm: LLMProvider | None = None
        self.orchestrator: Orchestrator | None = None

    async def startup(self) -> None:
        self.mcbp = MCBPClient(self.settings)
        await self.mcbp.startup()
        self.llm = build_provider(self.settings)
        self.orchestrator = Orchestrator(self.settings, self.mcbp, self.llm)

    async def shutdown(self) -> None:
        if self.mcbp is not None:
            await self.mcbp.shutdown()


container = Container()


def get_mcbp() -> MCBPClient:
    assert container.mcbp is not None, "container not started"
    return container.mcbp


def get_orchestrator() -> Orchestrator:
    assert container.orchestrator is not None, "container not started"
    return container.orchestrator
