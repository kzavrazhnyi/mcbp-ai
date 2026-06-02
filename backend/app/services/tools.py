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
    return await c.list_catalog(a["type"], a.get("cursor"), a.get("limit", 50),
                                a.get("q"), a.get("fields"))


async def _get_documents(c: MCBPClient, a: dict) -> Any:
    return await c.list_documents(a["type"], a.get("from"), a.get("to"),
                                  a.get("cursor"), a.get("limit", 100),
                                  a.get("filters"), a.get("fields"))


async def _get_schema(c: MCBPClient, a: dict) -> Any:
    return await c.document_schema(a["type"])


async def _register_balance(c: MCBPClient, a: dict) -> Any:
    # Accept dimensions either nested under "filters" or as top-level keys (besides "type").
    filters = dict(a.get("filters") or {})
    for k, v in a.items():
        if k not in ("type", "filters"):
            filters[k] = v
    return await c.register_balance(a["type"], filters)


async def _filter_catalog(c: MCBPClient, a: dict) -> Any:
    return await c.filter_catalog(
        a["type"], a.get("filters") or {}, a.get("orderby"),
        bool(a.get("desc", False)), bool(a.get("exclude_groups", False)),
        a.get("limit", 100), a.get("cursor"), a.get("fields"))


async def _list_metadata(c: MCBPClient, a: dict) -> Any:
    return await c.list_metadata(a["metadata"])


async def _describe_metadata(c: MCBPClient, a: dict) -> Any:
    return await c.describe_metadata(a["metadata"], a["type"])


async def _get_object(c: MCBPClient, a: dict) -> Any:
    return await c.get_object(a["metadata"], a["type"], a["id"])


# --- Registry ---
# ПОРЯДОК ВАЖЛИВИЙ: MockProvider викликає TOOLS[0], тож search_catalog лишається першим.
# Інструменти інтроспекції додані в кінець; пріоритет «спершу структура» задано в SYSTEM_PROMPT.
TOOLS: dict[str, Tool] = {
    "search_catalog": Tool(
        _def("search_catalog",
             "Шукає елементи довідника 1С (контрагенти, товари, користувачі тощо). "
             "Повертає сторінку записів з ref та полями.",
             {"type": {"type": "string", "description": "Тип довідника, напр. Контрагенты, Номенклатура"},
              "q": {"type": "string", "description": "Текст пошуку за назвою/кодом"},
              "fields": {"type": "array", "items": {"type": "string"},
                         "description": "Додаткові реквізити у рядках, напр. [\"Покупатель\",\"КодПоЕДРПОУ\"]"},
              "limit": {"type": "integer", "default": 50},
              "cursor": {"type": "string"}},
             ["type"]),
        _search_catalog),
    "get_documents": Tool(
        _def("get_documents",
             "Повертає документи 1С заданого типу за період. Дати у форматі YYYY-MM-DD. "
             "ВАЖЛИВО: за замовчуванням рядки містять лише стандартні поля (Number/Date/Posted/...) — "
             "БЕЗ контрагента й сум. Щоб відібрати документи КОНКРЕТНОГО контрагента (чи за іншим "
             "посилальним полем), спершу знайди його ref через search_catalog/filter_catalog, потім "
             "передай `filters`, напр. {\"Контрагент\": \"<uuid>\"} (значення — UUID з Ref.Data; для "
             "складеного типу — \"ІмяТипу:UUID\"). Імена полів бери з describe_metadata, не вгадуй. "
             "Через `fields` додай у кожен рядок потрібні реквізити шапки (напр. [\"Контрагент\", "
             "\"СуммаДокумента\"]), щоб бачити їх без drill-down. Для повних даних і табличних частин "
             "(номенклатура) — get_object за Ref.Data рядка.",
             {"type": {"type": "string", "description": "Тип документа, напр. ЗаказПокупателя"},
              "from": {"type": "string", "description": "Початок періоду YYYY-MM-DD"},
              "to": {"type": "string", "description": "Кінець періоду YYYY-MM-DD"},
              "filters": {"type": "object",
                          "description": "{ім'я_поля: значення}; для контрагента — {\"Контрагент\": \"<uuid>\"}"},
              "fields": {"type": "array", "items": {"type": "string"},
                         "description": "Додаткові реквізити шапки у рядках, напр. [\"Контрагент\",\"СуммаДокумента\"]"},
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
             "Повертає залишок по регістру накопичення (борг/взаєморозрахунки/залишки складу тощо) "
             "з фільтрами за ВИМІРАМИ регістру. Точні імена вимірів бери з describe_metadata "
             "(вид AccumulationRegisters) — не вгадуй (напр. вимір може зватися Контрагент, а не "
             "counterparty). Значення-посилання (контрагент, організація, номенклатура) передавай "
             "як UUID з Ref.Data. Приклад: {\"type\":\"...\",\"filters\":{\"Контрагент\":\"<uuid>\"}}.",
             {"type": {"type": "string", "description": "Ім'я регістру накопичення (з list_metadata)"},
              "filters": {"type": "object",
                          "description": "{ім'я_виміру: значення}; посилання — UUID, напр. {\"Контрагент\": \"<uuid>\"}"}},
             ["type"]),
        _register_balance),
    "list_metadata": Tool(
        _def("list_metadata",
             "Структура конфігурації 1С. metadata='all' → перелік об'єктів усіх видів одразу; "
             "metadata=Catalogs|Documents|InformationRegisters|AccumulationRegisters|Enums|Tasks|... → "
             "список об'єктів цього виду (ім'я + синонім, без реквізитів). "
             "Працює для будь-якої конфігурації. Виклич, щоб дізнатися реальні імена типів, "
             "замість того щоб їх вгадувати.",
             {"metadata": {"type": "string",
                           "description": "Вид метаданих (Catalogs, Documents, InformationRegisters, ...) або 'all'"}},
             ["metadata"]),
        _list_metadata),
    "describe_metadata": Tool(
        _def("describe_metadata",
             "Детальний опис одного об'єкта метаданих у вигляді дерева: реквізити з типами і "
             "табличні частини з їх реквізитами (для регістрів — виміри/ресурси/реквізити; "
             "для перелічень — значення). Використовуй, щоб дізнатися ТОЧНІ імена полів "
             "(напр. чи є прапорець Pokupatel/Postavshchik) ПЕРЕД фільтрацією чи читанням даних. "
             "Не вигадуй імена полів — спершу подивись опис.",
             {"metadata": {"type": "string",
                           "description": "Вид: Catalogs, Documents, InformationRegisters, ..."},
              "type": {"type": "string",
                       "description": "Ім'я об'єкта, напр. Контрагенты, ЗаказПокупателя, MCBP_StatusFunctions"}},
             ["metadata", "type"]),
        _describe_metadata),
    "filter_catalog": Tool(
        _def("filter_catalog",
             "Серверна вибірка елементів довідника з УНІВЕРСАЛЬНИМ фільтром за будь-якими полями "
             "та сортуванням (фільтрація і типізація — на боці 1С, надійно). "
             "`filters` — словник {ім'я_поля: значення}, поля бери з `describe_metadata` (реальні "
             "імена, напр. Покупатель, Постачальник, Наименование). Рівність; для рядка зі знаком "
             "% — пошук LIKE. `orderby` — поле сортування (напр. Наименование), `desc` — за спаданням. "
             "`exclude_groups=true` виключає групи-папки. Працює для будь-якої конфігурації. "
             "Використовуй це (а не search_catalog), коли треба відфільтрувати/відсортувати за полем.",
             {"type": {"type": "string", "description": "Тип довідника, напр. Контрагенты"},
              "filters": {"type": "object",
                          "description": "{ім'я_поля: значення}, напр. {\"Покупатель\": true}"},
              "orderby": {"type": "string", "description": "Поле сортування, напр. Наименование"},
              "desc": {"type": "boolean", "default": False},
              "exclude_groups": {"type": "boolean", "default": False},
              "fields": {"type": "array", "items": {"type": "string"},
                         "description": "Додаткові реквізити у рядках, напр. [\"Покупатель\",\"КодПоЕДРПОУ\"]"},
              "limit": {"type": "integer", "default": 100}},
             ["type"]),
        _filter_catalog),
    "get_object": Tool(
        _def("get_object",
             "ПОВНА інформація про ОДИН конкретний об'єкт (усі реквізити + табличні частини). "
             "Списки (search_catalog/filter_catalog/get_documents) повертають лише стандартні поля "
             "(Code, Description, Date, Number, ... + Ref). Коли треба деталі по конкретному запису — "
             "виклич get_object, передавши його id (UUID з поля Ref.Data у рядку списку).",
             {"metadata": {"type": "string", "description": "Вид: Catalogs, Documents, Tasks, ..."},
              "type": {"type": "string", "description": "Тип об'єкта, напр. Контрагенты, ЗаказПокупателя"},
              "id": {"type": "string", "description": "UUID об'єкта (Ref.Data зі списку)"}},
             ["metadata", "type", "id"]),
        _get_object),
}


def tool_defs(allowed: list[str] | None = None) -> list[ToolDef]:
    items = TOOLS.values() if allowed is None else (TOOLS[n] for n in allowed if n in TOOLS)
    return [t.definition for t in items]
