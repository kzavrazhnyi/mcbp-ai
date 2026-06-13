# mcbp-ai

ШІ-бекенд для керованої моделлю роботи з даними **MCBP+** на платформі **BAS**
([bas-soft.eu](https://www.bas-soft.eu/) — напр. BAS Малий бізнес, BAS Бухгалтерія,
BAS Управління торгівлею) через HTTP-сервіс `MCBP_AI` (`/ai/v1/...`).

## Архітектура

```
Frontend ──REST/SSE──► ЦЕЙ BACKEND ──REST+Basic──► BAS: HTTPService.MCBP_AI
                       • LLM tool-loop              • контракт /ai/v1
                       • нормалізація помилок        • пагінація, HTTP-коди
```

**Потоками даних керує модель.** На запит користувача LLM сама обирає інструменти
(`search_catalog`, `get_documents`, `get_schema`, `get_register_balance`), backend
виконує їх проти BAS і повертає результат моделі — до фінальної відповіді.

Дві абстракції, обидві перемикаються через `.env`:
- `MCBPClient` (`app/clients/mcbp.py`) — http + вбудований **mock** (`MCBP_ONEC_MOCK=true`);
- `LLMProvider` (`app/llm/providers.py`) — `anthropic`, `openai`, **`mock`** (без ключів).

## Структура репозиторію

- **`backend/`** — FastAPI-бекенд (код, тести, веб-інтерфейс `frontend/`).
  Деталі та запуск — у [`backend/README.md`](backend/README.md).
- **`ANALYSIS_REPORT.md`** — аналіз конфігурації MCBP+ та API-довідник інтеграції.
- **`.claude/`** + **`CLAUDE.md`** + **`LIMITS.md`** — конфігурація Claude Code для цього проєкту
  (агенти, правила, скіли, MCP). Опис — у розділі [Claude Code конфігурація](#claude-code-конфігурація).

## Швидкий старт (mock-режим, без BAS і без ключів LLM)

Найпростіше — bootstrap-скрипт (створює `.venv`, ставить залежності, копіює `.env`):

```bash
cd backend
./setup.sh                           # macOS/Linux; Windows: .\setup.ps1
source .venv/bin/activate
uvicorn app.main:app --reload        # Swagger: http://localhost:8000/docs
pytest                               # smoke-тести проганяють tool-loop у mock
```

Або вручну:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

Веб-інтерфейс: `http://localhost:8000/` (редірект на `/ui/`).

## Конфігурація

Усі секрети — через змінні оточення (`backend/.env`, шаблон у `backend/.env.example`).
Файл `.env` навмисно не входить до репозиторію.

---

## Claude Code конфігурація

Проєкт укомплектовано конфігом Claude Code (тариф **pro-20**, solo-розробник, платформа
**macOS**). Усі агенти працюють на `sonnet` — деталі бюджету у `LIMITS.md`.

### Що входить

| Категорія | Кількість |
|---|---|
| Агенти | 5 |
| Правила (`rules/`) | 11 |
| Скіли | 12 (3 community + 6 universal-core + 3 custom-gap) |
| MCP-сервери | 1 (`context7`) |

**Агенти:** `developer`, `api-client-engineer`, `claude-integration-specialist`, `debugger`, `reviewer`.

**Кастомні скіли під проєкт:** `mcbp-onec-integration` (контракт 1С/BAS MCBP+ по HTTP),
`model-tool-orchestration-loop` (цикл «питання → LLM → tool-call → BAS → відповідь»),
`claude-api-tool-use` (Anthropic SDK: tool-use, стрімінг, prompt caching).

> 3 community-скіли (`fastapi-python`, `pytest-coverage`, `ruff-recursive-fix`) поставляються
> **вбудовано** в `.claude/skills/` — `npx skills add` не потрібен.

### Хто за що відповідає

| Кажеш... | Диспатчиться до |
|---|---|
| «додай ендпоінт», «полагодь роутер» | `developer` |
| «mcbp клієнт», «реєстр інструментів», «search_catalog» | `api-client-engineer` |
| «tool-use loop», «SSE», «anthropic», «ai_orchestrator» | `claude-integration-specialist` |
| «баг», «падає», «не працює», «тест червоний» | `debugger` |
| «рев'ю», «аудит», «перед пушем» | `reviewer` |

Оркестратор диспатчить по одному агенту на задачу. Максимум 2 агенти паралельно;
`reviewer` завжди серійно (read-only, без Edit/Write).

### Передумови

1. **Python 3.11+** (macOS — рекомендується через `uv`).
2. **Node.js** (для `npx` — MCP-сервер `context7`).
3. **context7 API-ключ** — отримати на https://context7.com/dashboard.
4. **Секрети проєкту** — у `backend/.env` (див. розділ «Конфігурація» вище:
   `ANTHROPIC_API_KEY`, опційно `OPENAI_API_KEY`, `MCBP_ONEC_URL/USER/PASSWORD`).

### Налаштування Claude Code

```bash
# 1. Ключ context7 (перезапусти Claude Code після цього)
export CONTEXT7_API_KEY=ctx7sk-...
# Або постійно в ~/.zshrc:
echo 'export CONTEXT7_API_KEY=ctx7sk-...' >> ~/.zshrc
```

Колеги на Windows можуть використати:
```powershell
[Environment]::SetEnvironmentVariable("CONTEXT7_API_KEY", "ctx7sk-...", "User")
```

Конфіг уже лежить у репозиторії (`.claude/`, `CLAUDE.md`, `.mcp.json`, `LIMITS.md`).
Відкрий Claude Code у корені проєкту — на першому запуску буде запит увімкнути MCP `context7`.

### Як розширювати

- **Додати інструмент:** `api-client-engineer` → `clients/mcbp.py` + `services/tools.py` +
  схема в реєстрі інструментів.
- **Змінити LLM-провайдера:** `settings.llm_provider` у `backend/.env`
  (`anthropic` / `openai` / `mock`); абстракцію тримає `claude-integration-specialist`.
- **Додати правило:** новий файл `.claude/rules/<name>.md` за зразком наявних.
