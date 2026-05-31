# mcbp-ai-backend

Окремий Python-backend для ШІ-керованої роботи з даними MCBP+ (1С).
Працює в парі з **новим** HTTP-сервісом `MCBP_AI` (`/ai/v1/...`), окремо від legacy `MCBP_Exchange`.

## Ідея

```
Frontend (потім)  ──REST/SSE──►  ЦЕЙ BACKEND  ──REST+Basic──►  1С: HTTPService.MCBP_AI
                                 • LLM tool-loop                • чистий /ai/v1 контракт
                                 • нормалізація помилок          • пагінація, реальні HTTP-коди
```

**Потоки даних керує модель.** На запит користувача LLM сам обирає інструменти
(`search_catalog`, `get_documents`, `get_schema`, `get_register_balance`),
backend виконує їх проти 1С і повертає результат моделі — до фінальної відповіді.

## Дві абстракції (обидві обираються через `.env`)

| Абстракція | Реалізації | Навіщо |
|---|---|---|
| `MCBPClient` (`app/clients/mcbp.py`) | http + вбудований **mock** (`MCBP_ONEC_MOCK=true`) | підняти й тестувати backend **до** готовності 1С |
| `LLMProvider` (`app/llm/providers.py`) | `anthropic`, `openai`, **`mock`** | змінювати модель без зміни логіки; `mock` працює без ключів |

## Запуск (mock-режим, без 1С і без LLM-ключів)

```bash
cd C:\PYTHON\mcbp\backend
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env            # за замовчуванням MCBP_ONEC_MOCK=true, MCBP_LLM_PROVIDER=mock
uvicorn app.main:app --reload     # Swagger: http://localhost:8000/docs
pytest                            # smoke-тести проганяють увесь tool-loop у mock-режимі
```

**Веб-інтерфейс:** після запуску відкрий **http://localhost:8000/** — це чат
(`frontend/`, vanilla HTML/JS/CSS). Корінь редіректить на `/ui/`. Чат шле запити в
`POST /ai/v1/ai/query` зі стрімінгом (fetch + ReadableStream, бо POST не вміє EventSource)
і показує живий прогрес tool-calls + фінальну відповідь.

Перевірка API:
```bash
curl localhost:8000/ai/v1/health
curl "localhost:8000/ai/v1/catalogs/Counterparties?q=ТОВ"
curl -X POST localhost:8000/ai/v1/ai/query -H 'Content-Type: application/json' \
  -d '{"message":"Скільки замовлень від ТОВ за травень і чи є борг?","stream":false}'
```

## Перехід на живу 1С / реальну модель

1. `.env`: `MCBP_ONEC_MOCK=false`, заповнити `MCBP_ONEC_*` (Basic-логін до публікації `MCBP_AI`).
2. `.env`: `MCBP_LLM_PROVIDER=anthropic` (модель `claude-opus-4-8`) або `openai` + ключ.

> Сервіс `MCBP_AI` у 1С автентифікує через внутрішній «ключ» бази + HTTP Basic
> (Bearer — поки точка розширення). Тому backend ходить через **Basic**, без обміну на токен.

## Структура

```
app/
  core/      config.py, errors.py, deps.py
  clients/   mcbp.py             — async-клієнт до 1С + mock + нормалізація помилок
  llm/       base.py, providers.py — абстракція LLM (anthropic/openai/mock)
  services/  tools.py, ai_orchestrator.py — реєстр інструментів + цикл model→tool→model
  routers/   system.py, data.py, ai.py
  main.py
tests/       test_smoke.py
```
