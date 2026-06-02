# Технічний опис backend (`mcbp-ai`)

> Повний технічний опис серверної частини за станом коду в `backend/`.
> Призначення: ШІ-сервіс, у якому **модель сама керує потоками даних** —
> на запит користувача LLM вирішує, які інструменти викликати, а backend
> виконує їх проти 1С (HTTP-сервіс `MCBP_AI`, контракт `/ai/v1`).

---

## 1. Загальний огляд

```
Frontend (vanilla JS)  ──REST / SSE──►  BACKEND (FastAPI)  ──REST + Basic──►  1С: HTTPService.MCBP_AI
                                         • LLM tool-loop                       • контракт /ai/v1
                                         • нормалізація помилок                 • реальні HTTP-коди, пагінація
```

Ключова ідея: **data flow керує модель**. Користувач формулює запит природною
мовою → оркестратор передає його LLM разом з описом інструментів → модель обирає
послідовність викликів (`search_catalog` → `get_documents` → `get_register_balance`
тощо) → backend виконує кожен проти 1С і повертає результат моделі → цикл триває
до фінальної відповіді або до ліміту ітерацій.

Дві центральні абстракції, обидві перемикаються через `.env` **без зміни коду**:

| Абстракція | Файл | Реалізації |
|---|---|---|
| `MCBPClient` (доступ до 1С) | `app/clients/mcbp.py` | `http` + вбудований **mock** (`MCBP_ONEC_MOCK=true`) |
| `LLMProvider` (модель) | `app/llm/providers.py` | `anthropic`, `openai`, **`mock`** (без ключів) |

Завдяки mock-режимам backend піднімається і повністю тестується **без 1С і без
ключів LLM**.

---

## 2. Технологічний стек

| Компонент | Версія (мін.) | Роль |
|---|---|---|
| Python | 3.11 | мова, async/await |
| FastAPI | 0.115 | веб-фреймворк, DI, OpenAPI |
| Uvicorn | 0.32 | ASGI-сервер |
| httpx | 0.27 | async-HTTP-клієнт до 1С |
| pydantic / pydantic-settings | 2.9 / 2.5 | валідація, конфіг із `.env` |
| anthropic | 0.40 | SDK Claude (lazy import) |
| openai | 1.54 | SDK OpenAI (lazy import) |
| pytest / pytest-asyncio / respx / ruff | dev | тести, лінт |

Пакет описано в `backend/pyproject.toml` (`name = "mcbp-ai-backend"`, `app*` —
єдиний пакет; фронтенд і тести не пакуються). SDK моделей імпортуються **ліниво**
в конструкторах провайдерів, тож mock/тести не вимагають їх наявності.

---

## 3. Архітектура та структура каталогів

Чітка шарова структура: роутери (HTTP) → DI-контейнер → сервіси/клієнти.

```
backend/
  app/
    main.py                — точка входу FastAPI, lifespan, CORS, маршрути, статика
    core/
      config.py            — Settings (pydantic-settings, читає .env)
      deps.py              — Container: один MCBPClient + LLMProvider + Orchestrator
      errors.py            — типізовані MCBPError (code + http_status)
    clients/
      mcbp.py              — async-клієнт до 1С /ai/v1 + mock + класифікація помилок
    llm/
      base.py              — Protocol LLMProvider + dataclass-и кроку tool-calling
      providers.py         — Anthropic / OpenAI / Mock + build_provider()
    services/
      tools.py             — реєстр інструментів (ToolDef + async-executor)
      ai_orchestrator.py   — цикл model→tool→model (run / stream)
    routers/
      system.py            — /ai/v1/health, /ai/v1/auth/token
      data.py              — /ai/v1/catalogs|documents|objects|registers
      ai.py                — /ai/v1/ai/query (JSON + SSE)
  frontend/                — vanilla HTML/JS/CSS (чат), монтується на /ui
  tests/                   — smoke-тести (mock-режим)
  diagnose.py              — CLI-діагностика зв'язку backend ↔ 1С
  pyproject.toml, requirements.txt, .env.example, setup.ps1, setup.sh
```

**Принцип залежностей:** роутери не створюють об'єкти самі — вони беруть готові
екземпляри з `Container` через `get_mcbp()` / `get_orchestrator()`. Це дає єдиний
пул з'єднань до 1С і один стан провайдера на весь процес.

---

## 4. Конфігурація (`app/core/config.py`)

`Settings(BaseSettings)` читає `.env` (UTF-8), зайві ключі ігнорує
(`extra="ignore"`), підтримує доступ і за іменем поля, і за alias. `get_settings()`
кешується (`@lru_cache`).

| Поле | Env-змінна | Дефолт | Призначення |
|---|---|---|---|
| `app_name` | — | `mcbp-ai-backend` | назва застосунку |
| `env` | `MCBP_ENV` | `dev` | `dev`/`prod` (керує CORS) |
| `log_level` | `MCBP_LOG_LEVEL` | `INFO` | рівень логів |
| `onec_mock` | `MCBP_ONEC_MOCK` | `true` | `true` → працювати без 1С |
| `onec_base_url` | `MCBP_ONEC_BASE_URL` | `http://localhost/base/hs` | база URL `MCBP_AI` |
| `onec_user` | `MCBP_ONEC_USER` | `""` | логін Basic-auth до 1С |
| `onec_password` | `MCBP_ONEC_PASSWORD` | `""` | пароль Basic-auth |
| `onec_timeout_s` | `MCBP_ONEC_TIMEOUT_S` | `30` | таймаут запиту |
| `onec_pool_max` | `MCBP_ONEC_POOL_MAX` | `10` | макс. з'єднань у пулі |
| `llm_provider` | `MCBP_LLM_PROVIDER` | `mock` | `mock`/`anthropic`/`openai` |
| `anthropic_api_key` | `ANTHROPIC_API_KEY` (alias `MCBP_ANTHROPIC_API_KEY`) | `""` | ключ Claude |
| `anthropic_model` | `MCBP_ANTHROPIC_MODEL` | `claude-opus-4-8` | модель Claude |
| `openai_api_key` | `OPENAI_API_KEY` (alias `MCBP_OPENAI_API_KEY`) | `""` | ключ OpenAI |
| `openai_model` | `MCBP_OPENAI_MODEL` | `gpt-4o` | модель OpenAI |
| `llm_max_tool_iterations` | `MCBP_LLM_MAX_TOOL_ITERATIONS` | `8` | ліміт кроків tool-loop |

Ключі моделей читаються зі **стандартних** імен (`ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`) — щоб їх підхоплювали й самі SDK — з `MCBP_`-аліасом як запасним.
Шаблон значень — у `backend/.env.example`; реальний `.env` у git не входить.

---

## 5. Життєвий цикл застосунку (`app/main.py`)

- Усе монтується під префіксом `/ai`, щоб дзеркалити простір імен 1С-сервісу.
- `lifespan` на старті викликає `container.startup()` (створює клієнт 1С + провайдер
  + оркестратор), на зупинці — `container.shutdown()` (закриває пул httpx).
- **CORS:** `allow_origins=["*"]` лише коли `env == "dev"`, інакше порожньо;
  методи `GET/POST/OPTIONS`, заголовки `Authorization`, `Content-Type`.
- **Обробник помилок:** будь-який `MCBPError` → `JSONResponse` зі статусом
  `exc.http_status` і тілом `{"error": {"code", "message"}}`.
- **Маршрути:** `system`, `data`, `ai` (усі з префіксом `/ai`).
- **Корінь `/`:** редірект на `/ui/`, якщо є тека `frontend/`; інакше — інфо-JSON.
- **Статика:** `frontend/` монтується як `StaticFiles(html=True)` на `/ui`.

### DI-контейнер (`app/core/deps.py`)

`Container` тримає `settings`, `mcbp`, `llm`, `orchestrator`. Глобальний екземпляр
`container`; геттери `get_mcbp()` / `get_orchestrator()` стверджують, що контейнер
піднятий. Один екземпляр кожного сервісу на весь процес → спільний пул з'єднань.

---

## 6. Клієнт 1С (`app/clients/mcbp.py`)

`MCBPClient` — тонкий async-клієнт до `MCBP_AI`. Дві задачі:

1. **Транспорт.** `httpx.AsyncClient` з постійним пулом (1С перевикористовує сеанси
   ~20 с, тож пул важливий), Basic-auth у заголовку, `Content-Type: application/json`,
   таймаут і ліміт з'єднань із конфігу. Створюється у `startup()`, закривається у
   `shutdown()` (у mock-режимі не створюється взагалі).
2. **Нормалізація відповідей.** Новий `MCBP_AI` повертає **справжні HTTP-коди**:
   `404 → NotFoundError`, `>=400 → UpstreamError`. Додатково — **захисне**
   виявлення legacy-форми `MCBP_Exchange` (`success:false` + рядок у
   `data`/`answer`/`error`) і класифікація через `_classify_legacy_error`.

`_ERROR_MARKERS` мапить відомі рядки 1С на типізовані винятки:
`Key not found → KeyMismatchError`, `MCBP Plus not found → PlusRequiredError`,
`not found! → ParameterError`, `format YYYYMMDD → ParameterError`, решта →
`UpstreamError`.

**High-level методи** (поверхня, якою користується решта застосунку):

| Метод | HTTP до 1С |
|---|---|
| `health()` | `GET /ai/v1/health` |
| `list_catalog(type, cursor, limit, q)` | `GET /ai/v1/catalogs/{type}` |
| `list_documents(type, from, to, cursor, limit)` | `GET /ai/v1/documents/{type}` |
| `document_schema(type)` | `GET /ai/v1/documents/{type}/schema` |
| `create_object(type, body, information_base)` | `POST /ai/v1/objects/{type}?InformationBase=` |
| `register_balance(type, filters)` | `GET /ai/v1/registers/{type}/balance` |
| `push_ai_context(body)` | `POST /ai/v1/ai/context` |

**Mock-дані** (`_mock_response`) навмисно повторюють форму реальної demo-бази
`basmbdemo` (українська типова): кириличні типи (`Контрагенты`/`ЗаказПокупателя`),
латинізовані ключі полів (`Kod`, `Naimenovanie`, `KodPoEDRPOU`), курсор пагінації.

---

## 7. Шар LLM (`app/llm/`)

### Контракт (`base.py`)

- `ToolDef(name, description, parameters)` — опис інструмента для моделі (JSON-schema).
- `ToolInvocation(id, name, arguments)` — виклик інструмента моделлю.
- `LLMStep(text, tool_calls, raw)` — результат одного ходу; `wants_tools` → чи є
  виклики; `raw` зберігає нативний об'єкт для коректного round-trip у діалог.
- `LLMProvider` (`Protocol`): `step(system, messages, tools)`,
  `assistant_message(step)`, `tool_result_message(call, result)`. Історія діалогу
  ведеться у провайдер-нативному форматі — кожен провайдер сам конвертує її у своє API.

### Провайдери (`providers.py`)

- **AnthropicProvider** — `messages.create` з `max_tokens=4096`,
  `thinking={"type":"adaptive"}` (адаптивне мислення на Opus 4.8), **prompt caching**
  статичного префікса (`system` + останній `tool` позначено
  `cache_control: ephemeral`). Розбирає блоки `text` / `tool_use`. Tool-result
  повертається роллю `user` з блоком `tool_result`.
- **OpenAIProvider** — `chat.completions.create`; `system` додається першим
  повідомленням; інструменти у форматі `{"type":"function", ...}`; tool-result —
  роллю `tool` з `tool_call_id`.
- **MockProvider** — детермінований двокроковий цикл: перший хід викликає перший
  інструмент (з підставленим обов'язковим аргументом `Counterparties`), другий —
  віддає фіксовану відповідь. Дозволяє прогнати весь шлях оркестрації без ключів.
- `build_provider(settings)` обирає реалізацію за `llm_provider`.

---

## 8. Інструменти (`app/services/tools.py`)

Реєстр — місток між tool-call моделі та методами `MCBPClient`. Кожен інструмент =
`ToolDef` (що бачить модель) + async-`executor` (що викликає 1С).

| Інструмент | Обов'язкові | Опційні | Викликає |
|---|---|---|---|
| `search_catalog` | `type` | `q`, `limit`(50), `cursor` | `list_catalog` |
| `get_documents` | `type` | `from`, `to` (YYYY-MM-DD), `limit`(100), `cursor` | `list_documents` |
| `get_schema` | `type` | — | `document_schema` |
| `get_register_balance` | `type` | `counterparty` (ref) | `register_balance` |
| `list_metadata` | `metadata` (`all` або вид) | — | `list_metadata` |
| `describe_metadata` | `metadata`, `type` | — | `describe_metadata` |
| `filter_catalog` | `type` | `filters{поле:значення}`, `orderby`, `desc`, `exclude_groups`, `limit` | `filter_catalog` |

`filter_catalog` — **універсальний серверний фільтр** за будь-якими полями (рівність; рядок з `%` → LIKE)
+ сортування + виключення груп. Імена полів — реальні (з `describe_metadata`, російські
ідентифікатори); валідація і типізація на боці 1С (анти-інʼєкція; посилання → 422).

Останні два — **інтроспекція структури конфігурації** (через `/ai/v1/metadata`): модель
спершу дізнаєтся реальні види/об'єкти/поля, а не вгадує їх. Працює для будь-якої
конфігурації (читання суто через `Metadata.*`).

`tool_defs(allowed)` віддає або всі описи, або лише дозволений підмножину (на
запит можна обмежити перелік інструментів через `allowed_tools`).

---

## 9. Оркестратор (`app/services/ai_orchestrator.py`)

Ядро «model-driven data flow». `SYSTEM_PROMPT` інструктує модель: даних напряму
немає — лише через інструменти; спершу знайти `ref`, потім тягти документи/залишки;
відповідати українською, стисло, з числами; помилки доступу пояснювати, дані не
вигадувати.

Два режими, обидва крутять цикл до `llm_max_tool_iterations`:

- **`run(message, allowed_tools)`** — non-streaming. Повертає
  `{"answer", "tool_calls"}`. На кожній ітерації: `llm.step` → якщо немає
  tool-calls, повертає фінал; інакше виконує кожен виклик і додає результат у діалог.
- **`stream(message, allowed_tools)`** — async-генератор подій для SSE:
  `{"type":"tool_call",...}`, `{"type":"tool_result", "ok": bool}`,
  `{"type":"answer","text":...}`.

`_execute_tool` ловить помилки безпечно: `MCBPError` → `{"error":{code,message}}`,
`KeyError/TypeError` → `BAD_ARGUMENTS`, невідомий інструмент → `unknown tool`.
Помилка інструмента **не валить** цикл — вона повертається моделі як результат.

---

## 10. HTTP API (роутери)

Усе під `/ai`. Параметри валідуються FastAPI/pydantic; `MCBPError` → коректний код
через обробник у `main.py`.

### `system.py`
- `GET /ai/v1/health` → `{data:{backend, mock_1c, llm_provider, upstream}}`;
  health не падає — помилку upstream загортає в `{error}`.
- `POST /ai/v1/auth/token` → заглушка `{data:{token:"dev-token", type:"bearer"}}`
  (реальний обмін creds→token заплановано).

### `data.py` (проксі контракту `MCBP_AI` для фронтенду/інтеграцій)
- `GET /ai/v1/catalogs/{type}` — `q`, `cursor`, `limit` (1–1000, дефолт 50).
- `GET /ai/v1/documents/{type}/schema`.
- `GET /ai/v1/documents/{type}` — `from`(alias), `to`, `cursor`, `limit` (дефолт 100).
- `POST /ai/v1/objects/{type}` — `InformationBase` (обов'язк., query) + JSON-тіло.
- `GET /ai/v1/registers/{type}/balance` — усі query-параметри як фільтри.

### `ai.py`
- `POST /ai/v1/ai/query` — тіло `{message, stream, allowed_tools}`.
  `stream=false` → `{data:{answer, tool_calls}}`; `stream=true` →
  `StreamingResponse` (`text/event-stream`, кожна подія — `data: {json}\n\n`).

---

## 11. Модель помилок (`app/core/errors.py`)

Базовий `MCBPError(message, code, http_status)`; підкласи з фіксованими кодами:

| Клас | `code` | HTTP |
|---|---|---|
| `UpstreamError` | `UPSTREAM_ERROR` | 502 |
| `NotFoundError` | `NOT_FOUND` | 404 |
| `ParameterError` | `BAD_PARAMETER` | 400 |
| `KeyMismatchError` | `KEY_MISMATCH` | 502 |
| `PlusRequiredError` | `PLUS_REQUIRED` | 501 |

Назовні завжди єдина форма: `{"error": {"code", "message"}}`.

---

## 12. Frontend (`backend/frontend/`)

Vanilla HTML/JS/CSS без збірки (`index.html`, `styles.css`, `app.js` ~7 КБ).
Монтується як статика на `/ui` (корінь `/` редіректить туди). Чат шле
`POST /ai/v1/ai/query` зі стрімінгом (fetch + ReadableStream, бо POST не вміє
EventSource) і показує живий прогрес tool-calls та фінальну відповідь. Один origin
з API → у проді CORS не потрібен.

---

## 13. Тести (`backend/tests/`)

`conftest.py` примусово виставляє `MCBP_ONEC_MOCK=true` і `MCBP_LLM_PROVIDER=mock`
**до** імпорту застосунку і скидає кеш `get_settings` — тести ізольовані від `.env`.

`test_smoke.py` (через `TestClient`): health у mock-режимі; читання довідника
(кириличний тип `Контрагенты`); схема документа; **повний tool-loop** через
`/ai/v1/ai/query` (перевіряє, що mock-модель реально викликала `search_catalog`);
юніт на класифікацію legacy-помилок. Поточний стан: **5 passed**.

---

## 14. Діагностика (`backend/diagnose.py`)

Окремий CLI (`python diagnose.py`, напряму через httpx, без uvicorn) для перевірки
зв'язку з живою 1С. Покроково: (1) `health` — публікація + Basic-auth (розрізняє
401/404/5xx), (2) внутрішній «ключ» бази (`health.key`), (3) дані-метод `catalogs`
з перебором кандидатів імен, (4) регресія — службовий довідник не має давати «голий»
500. Дає людський вердикт по кожному кроку (термінал переводиться в UTF-8 для кирилиці).

---

## 15. Запуск і розгортання

**Локально (mock, без 1С і ключів):**
```bash
cd backend
.\setup.ps1                      # Windows; Linux/macOS: ./setup.sh
.\.venv\Scripts\Activate.ps1     # Linux/macOS: source .venv/bin/activate
uvicorn app.main:app --reload    # Swagger: http://localhost:8000/docs ; UI: /
pytest
```

**Перехід на живу 1С / реальну модель:**
1. `.env`: `MCBP_ONEC_MOCK=false`, заповнити `MCBP_ONEC_*` (Basic-логін до публікації `MCBP_AI`).
2. `.env`: `MCBP_LLM_PROVIDER=anthropic` (`claude-opus-4-8`) або `openai` + відповідний ключ.
3. `python diagnose.py` — переконатися, що публікація/ключ/дані-методи відповідають.

**Прод-міркування:** виставити `MCBP_ENV=prod` (закриває CORS `*`); запускати під
кількома воркерами uvicorn/gunicorn (стан в `Container` per-process — горизонтальне
масштабування безпечне); секрети — лише через оточення, не в образі.

---

## 16. Відомі обмеження / напрямки розвитку

- `POST /ai/v1/auth/token` — заглушка; реальна автентифікація фронтенду ще не зроблена.
- `push_ai_context` у клієнті є, але ще не виставлений окремим інструментом/роутером.
- Запис об'єктів (`create_object`) на боці 1С може залежати від розширення
  «MCBP Plus» (див. `ANALYSIS_REPORT.md`).
- Стрімінг моделі — на рівні подій оркестратора (tool_call/result/answer), а не
  токенів; за потреби можна додати токенний стрім від провайдерів.
- `StarletteDeprecationWarning` у тестах (TestClient/httpx) — некритично; за бажання
  закріпити сумісні версії.

> Споріднені документи: `README.md` (швидкий старт), `backend/README.md` (деталі
> запуску), `ANALYSIS_REPORT.md` (аналіз 1С MCBP+ та API-довідник інтеграції).
