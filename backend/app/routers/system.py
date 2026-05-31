"""Системні ендпоінти: health та (заглушка) обмін creds на токен."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import container, get_mcbp

router = APIRouter()


@router.get("/v1/health")
async def health() -> dict:
    mcbp = get_mcbp()
    try:
        upstream = await mcbp.health()
    except Exception as exc:  # noqa: BLE001 — health не має падати
        upstream = {"error": str(exc)}
    return {
        "data": {
            "backend": "ok",
            "mock_1c": container.settings.onec_mock,
            "llm_provider": container.settings.llm_provider,
            "upstream": upstream,
        }
    }


@router.post("/v1/auth/token")
async def issue_token() -> dict:
    # Заглушка: реальний обмін 1С-creds → токен буде, коли підключимо фронтенд/автентифікацію.
    return {"data": {"token": "dev-token", "type": "bearer"}}
