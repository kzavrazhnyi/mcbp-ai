"""AI orchestrator: runs the model→tool→model loop.

The model is given the MCBP_AI tools and decides which to call. We execute each
call against 1C, feed results back, and repeat until the model produces a final
answer or we hit the iteration cap. This is the 'model-driven data flow' core.
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from app.clients.mcbp import MCBPClient
from app.core.config import Settings
from app.core.errors import MCBPError
from app.llm.base import LLMProvider
from app.services.tools import TOOLS, tool_defs

log = logging.getLogger(__name__)
# Окремий логер під слід «ШІ ↔ API» (пишеться у спільний файл, див. logging_setup).
trace = logging.getLogger("mcbp.ai")


def _result_brief(result: Any) -> str:
    """Стислий підсумок результату інструмента для лога."""
    if isinstance(result, dict):
        if "error" in result:
            err = result["error"]
            if isinstance(err, dict):
                return f"ERROR {err.get('code')}: {err.get('message')}"
            return f"ERROR: {err}"
        data = result.get("data")
        if isinstance(data, list):
            return f"ok ({len(data)} rows)"
        return "ok"
    return "ok"

SYSTEM_PROMPT = (
    "Ти — асистент над даними системи MCBP+ на платформі BAS (bas-soft.eu — українські "
    "рішення на кшталт BAS Малий бізнес, BAS Бухгалтерія, BAS Управління торгівлею). "
    "Ти НЕ маєш даних безпосередньо — отримуй їх лише через надані інструменти. "
    "Плануй послідовність викликів: спершу знайди потрібні довідкові елементи (ref), "
    "потім тягни документи/залишки. Відповідай українською, стисло, з конкретними числами. "
    "Якщо інструмент повертає помилку доступу — поясни її користувачу, не вигадуй дані.\n"
    "ВАЖЛИВО про імена (`type` і поля): у конфігураціях BAS внутрішні ІМЕНА метаданих "
    "успадковані російськомовні, а їх СИНОНІМИ (підписи) — українські. В інструменти "
    "передавай саме ВНУТРІШНІ імена, а не українські синоніми (інакше NOT_FOUND / Unknown field). "
    "Приклади типів: `Контрагенты`, `Номенклатура`, `Организации`, `Договоры`, `БанковскиеСчета`, "
    "`ЗаказПокупателя`, `РеализацияТоваровУслуг`. Приклади полів: `Покупатель`, `Поставщик`, "
    "`Наименование`, `Код` (а не укр. синоніми `Покупець`, `Постачальник`, `Найменування`). "
    "Точні імена бери з `list_metadata`/`describe_metadata`, не вгадуй.\n"
    "СПЕРШУ ВИВЧАЙ СТРУКТУРУ. Конфігурація BAS може бути будь-якою — її будову "
    "дізнавайся через інструменти інтроспекції: `list_metadata` (які є види та об'єкти) і "
    "`describe_metadata` (реквізити об'єкта з типами і табличні частини; там для кожного поля є "
    "`name` — внутрішнє ім'я для запитів — і `synonym` — український підпис для користувача). "
    "Перш ніж ФІЛЬТРУВАТИ чи зчитувати дані за якоюсь ознакою (напр. «покупці», «постачальники», "
    "сума, дата) — виклич `describe_metadata`, щоб дізнатися ТОЧНЕ ім'я поля (напр. `Покупатель`, "
    "`Поставщик`) і його тип. Далі для самої вибірки за полем використовуй `filter_catalog` "
    "(серверний фільтр + сортування), а НЕ `search_catalog` — не фільтруй і не сортуй список вручну "
    "у себе в голові. Передавай реальні імена полів у `filters`, сортування — через `orderby`. "
    "Щоб не плутати елементи з групами-папками — став `exclude_groups=true`. "
    "Фільтруй лише за реально наявними полями; якщо потрібного поля немає — скажи про це, "
    "а не вигадуй результат.\n"
    "ОБСЯГ ДАНИХ. Списки (`search_catalog`, `filter_catalog`, `get_documents`) повертають лише "
    "СТАНДАРТНІ поля (Code, Description, Date, Number, DeletionMark, ... + `Ref`). Цього досить для "
    "переліків. Коли треба ПОВНІ дані конкретного запису (усі реквізити, табличні частини) — виклич "
    "`get_object`, передавши `id` = `Ref.Data` (UUID) з потрібного рядка списку. "
    "Виводь УСІ рядки, що повернула база; не обрізай список і не вигадуй кількість — якщо їх багато, "
    "так і скажи, скільки всього, і за потреби бери наступну сторінку за `cursor`.\n"
    "ВІДБІР ЗА ЗВ'ЯЗКОМ (контрагент, номенклатура, організація…). Списки документів за замовчуванням "
    "НЕ містять контрагента — тому НЕ можна визначити власника документа «на око» і НЕ можна "
    "приписувати йому всі документи періоду. Алгоритм для питань на кшталт «що купує/скільки замовив "
    "контрагент X»: (1) знайди X через `search_catalog`/`filter_catalog` і візьми його `Ref.Data` (UUID); "
    "(2) виклич `get_documents` з `filters={\"<поле-контрагент>\": \"<uuid>\"}` (точне ім'я поля — з "
    "`describe_metadata`; для складеного типу — \"ІмяТипу:UUID\"), за потреби додай `fields` щоб бачити "
    "контрагента/суму в рядках; (3) для товарної структури («ЩО саме купує») візьми табличні частини "
    "через `get_object` за `Ref.Data` потрібних документів. Те саме для залишків/боргу — `get_register_balance` "
    "з фільтром за виміром-контрагентом (UUID). Якщо фільтр за полем повертає 0 рядків — так і скажи "
    "(у контрагента немає таких документів), НЕ підставляй замість цього загальний список.\n"
    "НЕ ВГАДУЙ ТИПИ. Перш ніж звертатись до `get_documents`/`get_object` за типом — переконайся, що такий "
    "тип є у списку з `list_metadata` (вид Documents). Не використовуй типи з інших конфігурацій навмання "
    "(напр. РеализацияТоваровУслуг/РахунокНаОплату можуть бути відсутні) — звіряйся зі списком.\n"
    "АВТОНОМНІСТЬ — ДІЙ, НЕ ПЕРЕПИТУЙ ОЧЕВИДНЕ. Доводь задачу до кінцевого результату (числа, таблиці) "
    "самостійно. Не проси в користувача те, що можна отримати інструментами або розумним дефолтом:\n"
    "• Період не вказано → бери останні 12 місяців до поточної дати і ЗАЗНАЧ обраний діапазон у відповіді "
    "(користувач за потреби уточнить). \n"
    "• Джерело очевидне → обери сам (напр. ЗаказПокупателя для замовлень покупців) — не проси підтвердження "
    "тривіального. \n"
    "• Не повторюй ту саму інтроспекцію; з'ясовуй структуру мінімально потрібним числом викликів, далі "
    "одразу переходь до вибірки й агрегації даних — не витрачай кроки даремно. \n"
    "• Уточнення (якщо взагалі потрібні) став у КІНЦІ й лише коли лишилась справді бізнес-неоднозначність "
    "(напр. кілька різних регістрів дебіторки) або інструмент недоступний (помилка). Спершу видай усе, що "
    "вже можна порахувати, і тільки потім — короткий перелік того, що варто уточнити."
)


def system_prompt_with_context() -> str:
    """SYSTEM_PROMPT + поточна дата — щоб модель сама обирала відносні періоди (останні 12 міс тощо)."""
    from datetime import date
    return SYSTEM_PROMPT + f"\nПОТОЧНА ДАТА: {date.today().isoformat()} — використовуй її для відносних періодів."


class Orchestrator:
    def __init__(self, settings: Settings, mcbp: MCBPClient, llm: LLMProvider):
        self._s = settings
        self._mcbp = mcbp
        self._llm = llm
        self._history: dict[str, list[dict]] = {}  # conversation_id -> messages (без system)

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

    def _load_history(self, conversation_id: str) -> list[dict[str, Any]]:
        return list(self._history.get(conversation_id, []))

    def _save_history(self, conversation_id: str, messages: list[dict[str, Any]]) -> None:
        if len(messages) > 100:
            messages = messages[-100:]
        self._history[conversation_id] = messages

    async def run(
        self,
        message: str,
        conversation_id: str,
        allowed_tools: list[str] | None = None,
    ) -> dict:
        """Non-streaming: returns final answer + the tool calls that were made."""
        trace.info("QUERY: %s | conv=%s | allowed_tools=%s", message, conversation_id, allowed_tools or "all")
        messages: list[dict[str, Any]] = self._load_history(conversation_id)
        messages.append({"role": "user", "content": message})
        defs = tool_defs(allowed_tools)
        system = system_prompt_with_context()
        made: list[dict] = []

        for iteration in range(self._s.llm_max_tool_iterations):
            step = await self._llm.step(system, messages, defs)
            messages.append(self._llm.assistant_message(step))

            if not step.wants_tools:
                trace.info("ANSWER (%d chars): %s", len(step.text or ""), step.text)
                self._save_history(conversation_id, messages)
                return {"answer": step.text, "tool_calls": made, "conversation_id": conversation_id}

            for call in step.tool_calls:
                trace.info("[it %d] tool_call %s args=%s",
                           iteration + 1, call.name,
                           json.dumps(call.arguments, ensure_ascii=False))
                result = await self._execute_tool(call.name, call.arguments)
                trace.info("[it %d] tool_result %s → %s",
                           iteration + 1, call.name, _result_brief(result))
                made.append({"name": call.name, "arguments": call.arguments})
                messages.append(self._llm.tool_result_message(call, result))

        trace.warning("Перевищено ліміт кроків (%d)", self._s.llm_max_tool_iterations)
        self._save_history(conversation_id, messages)
        return {"answer": "Перевищено ліміт кроків обробки.", "tool_calls": made, "conversation_id": conversation_id}

    async def stream(
        self,
        message: str,
        conversation_id: str,
        allowed_tools: list[str] | None = None,
    ) -> AsyncIterator[dict]:
        """Streaming variant: yields SSE-friendly events (tool steps + final)."""
        trace.info("QUERY (stream): %s | conv=%s | allowed_tools=%s", message, conversation_id, allowed_tools or "all")
        messages: list[dict[str, Any]] = self._load_history(conversation_id)
        messages.append({"role": "user", "content": message})
        defs = tool_defs(allowed_tools)
        system = system_prompt_with_context()

        for iteration in range(self._s.llm_max_tool_iterations):
            step = await self._llm.step(system, messages, defs)
            messages.append(self._llm.assistant_message(step))

            if not step.wants_tools:
                trace.info("ANSWER (%d chars): %s", len(step.text or ""), step.text)
                self._save_history(conversation_id, messages)
                yield {"type": "answer", "text": step.text}
                return

            for call in step.tool_calls:
                trace.info("[it %d] tool_call %s args=%s",
                           iteration + 1, call.name,
                           json.dumps(call.arguments, ensure_ascii=False))
                yield {"type": "tool_call", "name": call.name, "arguments": call.arguments}
                result = await self._execute_tool(call.name, call.arguments)
                trace.info("[it %d] tool_result %s → %s",
                           iteration + 1, call.name, _result_brief(result))
                yield {"type": "tool_result", "name": call.name, "ok": "error" not in (result or {})}
                messages.append(self._llm.tool_result_message(call, result))

        trace.warning("Перевищено ліміт кроків (%d)", self._s.llm_max_tool_iterations)
        self._save_history(conversation_id, messages)
        yield {"type": "answer", "text": "Перевищено ліміт кроків обробки."}
