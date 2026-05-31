"""Діагностика зв'язку backend ↔ 1С HTTPService.MCBP_AI.

Запуск (з кореня backend, де лежить .env):
    python diagnose.py

Працює напряму через httpx + налаштування з .env (не потребує uvicorn).
Покроково перевіряє: публікацію → Basic-auth → внутрішній «ключ» → дані-методи,
і дає людський вердикт по кожному кроку.
"""

from __future__ import annotations

import base64
import sys

import httpx

from app.core.config import get_settings

# Термінал може бути cp1251 — друкуємо в UTF-8, щоб маркери/кирилиця не падали.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

OK = "[OK]"
FAIL = "[FAIL]"
WARN = "[!]"


def _hr(title: str) -> None:
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


def main() -> int:
    s = get_settings()

    _hr("КОНФІГ (.env)")
    print(f"  MCBP_ONEC_MOCK = {s.onec_mock}")
    print(f"  base_url       = {s.onec_base_url}")
    print(f"  user           = {s.onec_user!r}")
    print(f"  password set   = {'так' if s.onec_password else 'НІ (порожній)'}")

    if s.onec_mock:
        print("\n{WARN}  MCBP_ONEC_MOCK=true — діагностувати нема що, backend працює на синтетиці.")
        print("   Постав MCBP_ONEC_MOCK=false у .env, щоб бити в реальну базу.")
        return 0

    base = s.onec_base_url.rstrip("/")
    auth = base64.b64encode(f"{s.onec_user}:{s.onec_password}".encode("utf-8")).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

    client = httpx.Client(timeout=s.onec_timeout_s, follow_redirects=True)

    # ── Крок 1: health (без «ключа») ────────────────────────────────────
    _hr("КРОК 1 — GET /ai/v1/health (публікація + Basic-auth)")
    url = f"{base}/ai/v1/health"
    print(f"  GET {url}")
    try:
        r = client.get(url, headers=headers)
    except httpx.ConnectError as e:
        print(f"  {FAIL} НЕ ВДАЛОСЯ З'ЄДНАТИСЯ: {e}")
        print("     → веб-сервер (Apache/IIS) не запущено, або базу не опубліковано,")
        print("       або шлях /basmbdemo/hs/mcbp_ai невірний.")
        return 1
    except httpx.HTTPError as e:
        print(f"  {FAIL} Транспортна помилка: {e}")
        return 1

    print(f"  HTTP {r.status_code}")
    body_preview = r.text[:500]
    print(f"  body: {body_preview}")

    if r.status_code == 401:
        print("  {FAIL} 401 — Basic-auth відхилено. Перевір логін/пароль 1С (кирилиця 'Адміністратор'?).")
        print("     Спробуй службового користувача латиницею.")
        return 1
    if r.status_code == 404:
        print("  {FAIL} 404 — сервіс не знайдено. Перевір публікацію HTTP-сервісів і RootURL=mcbp_ai.")
        return 1
    if r.status_code >= 500:
        print("  {FAIL} 5xx — помилка на боці 1С. Дивись журнал реєстрації бази.")
        return 1
    if r.status_code != 200:
        print(f"  {WARN}  Неочікуваний код {r.status_code}.")
        return 1

    try:
        health = r.json()
    except Exception:
        print("  {WARN}  Відповідь не JSON — можливо, потрапили не на той сервіс.")
        return 1

    print(f"  {OK} Публікація і Basic-auth ОК. service={health.get('service')}")

    # ── Крок 2: внутрішній «ключ» бази ──────────────────────────────────
    _hr("КРОК 2 — внутрішній «ключ» бази (health.key)")
    key_ok = health.get("key")
    print(f"  health.key = {key_ok}")
    if key_ok is True:
        print("  {OK} Ключ збігається — дані-методи будуть доступні.")
    else:
        print("  {FAIL} Ключ НЕ збігається (GetAuditString != GetInformationBaseKeyExport).")
        print("     Дані-методи повертатимуть 403 KEY_MISMATCH.")
        print("     → Узгодь LicenseKey / поточну інфобазу в Catalog.MCBP_InformationBases.")

    # ── Крок 3: дані-метод (catalogs) — пробуємо кандидатів обох конвенцій ─
    _hr("КРОК 3 — GET /ai/v1/catalogs/{type} (дані-метод)")
    candidates = ["MCBP_Counterparties", "Контрагенты", "Номенклатура", "Организации"]
    found = False
    for t in candidates:
        url = f"{base}/ai/v1/catalogs/{t}"
        try:
            r = client.get(url, params={"limit": 3}, headers=headers)
        except httpx.HTTPError as e:
            print(f"  {t}: {FAIL} {e}")
            continue
        if r.status_code == 200:
            data = r.json().get("data", [])
            print(f"  {t}: HTTP 200  {OK} records={len(data)}")
            found = True
            break
        elif r.status_code == 403:
            print(f"  {t}: HTTP 403  {FAIL} проблема з ключем (Крок 2).")
        elif r.status_code == 404:
            print(f"  {t}: HTTP 404  (тип відсутній у цій базі)")
        else:
            print(f"  {t}: HTTP {r.status_code}  {r.text[:120]}")
    if not found:
        print(f"  {WARN}  Жоден кандидат не повернув 200 — підкажи реальне ім'я довідника.")

    # ── Крок 4: регресія BSL — службовий довідник не має давати 500 ──────
    _hr("КРОК 4 — регресія: catalogs/Пользователи (має бути 200 або {error}, не голий 500)")
    try:
        r = client.get(f"{base}/ai/v1/catalogs/Пользователи", params={"limit": 1}, headers=headers)
        ct = r.headers.get("content-type", "")
        is_json = "json" in ct.lower()
        print(f"  HTTP {r.status_code}  content-type={ct}")
        print(f"  body: {r.text[:200]}")
        if r.status_code == 200:
            print(f"  {OK} читається коректно.")
        elif is_json and r.status_code == 500:
            print(f"  {OK} 500, але загорнуто в {{error}} (try/except застосовано).")
        elif r.status_code == 500:
            print(f"  {WARN} 500 без JSON — розширення в базі ще НЕ оновлене (перезавантаж конфігурацію розширення).")
        else:
            print(f"  {WARN} код {r.status_code}.")
    except httpx.HTTPError as e:
        print(f"  {FAIL} {e}")

    client.close()
    _hr("ПІДСУМОК")
    print("  Кроки 1-2 + дані-метод [OK] — backend готовий проти basmbdemo.")
    print("  Запусти сервер:  uvicorn app.main:app --reload")
    return 0


if __name__ == "__main__":
    sys.exit(main())
