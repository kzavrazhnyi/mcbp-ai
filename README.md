# mcbp-ai

ШІ-бекенд для керованої моделлю роботи з даними **MCBP+** (1С:Підприємство 8)
через HTTP-сервіс `MCBP_AI` (`/ai/v1/...`).

## Архітектура

```
Frontend ──REST/SSE──► ЦЕЙ BACKEND ──REST+Basic──► 1С: HTTPService.MCBP_AI
                       • LLM tool-loop              • контракт /ai/v1
                       • нормалізація помилок        • пагінація, HTTP-коди
```

**Потоками даних керує модель.** На запит користувача LLM сама обирає інструменти
(`search_catalog`, `get_documents`, `get_schema`, `get_register_balance`), backend
виконує їх проти 1С і повертає результат моделі — до фінальної відповіді.

Дві абстракції, обидві перемикаються через `.env`:
- `MCBPClient` (`app/clients/mcbp.py`) — http + вбудований **mock** (`MCBP_ONEC_MOCK=true`);
- `LLMProvider` (`app/llm/providers.py`) — `anthropic`, `openai`, **`mock`** (без ключів).

## Структура репозиторію

- **`backend/`** — FastAPI-бекенд (код, тести, веб-інтерфейс `frontend/`).
  Деталі та запуск — у [`backend/README.md`](backend/README.md).
- **`ANALYSIS_REPORT.md`** — аналіз конфігурації MCBP+ та API-довідник інтеграції.

## Швидкий старт (mock-режим, без 1С і без ключів LLM)

Найпростіше — bootstrap-скрипт (створює `.venv`, ставить залежності, копіює `.env`):

```powershell
cd backend
.\setup.ps1                          # Windows; Linux/macOS: ./setup.sh
.\.venv\Scripts\Activate.ps1         # Linux/macOS: source .venv/bin/activate
uvicorn app.main:app --reload        # Swagger: http://localhost:8000/docs
pytest                               # smoke-тести проганяють tool-loop у mock
```

Або вручну:

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
copy .env.example .env
uvicorn app.main:app --reload
```

Веб-інтерфейс: `http://localhost:8000/` (редірект на `/ui/`).

## Конфігурація

Усі секрети — через змінні оточення (`backend/.env`, шаблон у `backend/.env.example`).
Файл `.env` навмисно не входить до репозиторію.
