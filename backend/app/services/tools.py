"""Tool registry: the bridge between LLM tool-calls and the 1C MCBP_AI service.

Each tool is (a) a ToolDef the model sees, and (b) an async executor that calls
MCBPClient. The model decides WHICH data to pull and in what order — that is the
'data flows are driven by the model' design from the requirement.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.clients.mcbp import MCBPClient
from app.llm.base import ToolDef

Executor = Callable[[MCBPClient, dict[str, Any]], Awaitable[Any]]


class Tool:
    def __init__(self, definition: ToolDef, executor: Executor):
        self.definition = definition
        self.executor = executor


def _def(name: str, description: str, properties: dict, required: list[str]) -> ToolDef:
    return ToolDef(
        name=name,
        description=description,
        parameters={"type": "object", "properties": properties, "required": required},
    )


# --- Executors ---
async def _search_catalog(c: MCBPClient, a: dict) -> Any:
    return await c.list_catalog(a["type"], a.get("cursor"), a.get("limit", 50), a.get("q"))


async def _get_documents(c: MCBPClient, a: dict) -> Any:
    return await c.list_documents(a["type"], a.get("from"), a.get("to"),
                                  a.get("cursor"), a.get("limit", 100))


async def _get_schema(c: MCBPClient, a: dict) -> Any:
    return await c.document_schema(a["type"])


async def _register_balance(c: MCBPClient, a: dict) -> Any:
    filters = {k: v for k, v in a.items() if k != "type"}
    return await c.register_balance(a["type"], filters)


# --- Registry ---
TOOLS: dict[str, Tool] = {
    "search_catalog": Tool(
        _def("search_catalog",
             "Шукає елементи довідника 1С (контрагенти, товари, користувачі тощо). "
             "Повертає сторінку записів з ref та полями.",
             {"type": {"type": "string", "description": "Тип довідника, напр. Counterparties, Products"},
              "q": {"type": "string", "description": "Текст пошуку за назвою/кодом"},
              "limit": {"type": "integer", "default": 50},
              "cursor": {"type": "string"}},
             ["type"]),
        _search_catalog),
    "get_documents": Tool(
        _def("get_documents",
             "Повертає документи 1С заданого типу за період. Дати у форматі YYYY-MM-DD.",
             {"type": {"type": "string", "description": "Тип документа, напр. SalesOrder"},
              "from": {"type": "string", "description": "Початок періоду YYYY-MM-DD"},
              "to": {"type": "string", "description": "Кінець періоду YYYY-MM-DD"},
              "limit": {"type": "integer", "default": 100},
              "cursor": {"type": "string"}},
             ["type"]),
        _get_documents),
    "get_schema": Tool(
        _def("get_schema",
             "Повертає схему (поля та їх типи) документа — корисно, щоб зрозуміти структуру перед читанням/записом.",
             {"type": {"type": "string"}},
             ["type"]),
        _get_schema),
    "get_register_balance": Tool(
        _def("get_register_balance",
             "Повертає залишок по регістру накопичення (напр. взаєморозрахунки/борг) з фільтрами.",
             {"type": {"type": "string", "description": "Тип регістру"},
              "counterparty": {"type": "string", "description": "ref контрагента"}},
             ["type"]),
        _register_balance),
}


def tool_defs(allowed: list[str] | None = None) -> list[ToolDef]:
    items = TOOLS.values() if allowed is None else (TOOLS[n] for n in allowed if n in TOOLS)
    return [t.definition for t in items]
