"""Thin async client for the 1C-side MCBP_AI HTTP service.

Two jobs:
  1. Talk to /ai/v1/* over httpx with a connection pool (1C reuses sessions for
     ~20s, so a persistent pool matters). Auth = HTTP Basic (як публікується сервіс).
  2. Normalise responses. The NEW MCBP_AI service returns real HTTP codes, but we
     still defensively detect the legacy "success:false + string in data/answer"
     shape (MCBP_Exchange) and raise typed MCBPError subclasses.

Set MCBP_ONEC_MOCK=true to run the whole backend with no 1C at all.
"""
from __future__ import annotations

import base64
from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import (
    KeyMismatchError,
    NotFoundError,
    ParameterError,
    PlusRequiredError,
    UpstreamError,
)

# Map known 1C error strings → typed exceptions.
_ERROR_MARKERS: list[tuple[str, type]] = [
    ("Key not found", KeyMismatchError),
    ("MCBP Plus not found", PlusRequiredError),
    ("not found!", ParameterError),  # "Parameter type not found!" etc.
    ("format YYYYMMDD", ParameterError),
]


def _classify_legacy_error(text: str) -> Exception:
    for marker, exc in _ERROR_MARKERS:
        if marker.lower() in text.lower():
            return exc(text)
    return UpstreamError(text)


class MCBPClient:
    def __init__(self, settings: Settings):
        self._s = settings
        self._mock = settings.onec_mock
        self._client: httpx.AsyncClient | None = None

    async def startup(self) -> None:
        if self._mock:
            return
        auth = base64.b64encode(
            f"{self._s.onec_user}:{self._s.onec_password}".encode()
        ).decode()
        self._client = httpx.AsyncClient(
            base_url=self._s.onec_base_url,
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            timeout=self._s.onec_timeout_s,
            limits=httpx.Limits(max_connections=self._s.onec_pool_max),
        )

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kw) -> Any:
        if self._mock:
            return _mock_response(method, path, kw)
        assert self._client is not None, "MCBPClient.startup() not called"
        try:
            resp = await self._client.request(method, path, **kw)
        except httpx.HTTPError as e:
            raise UpstreamError(f"transport error: {e}") from e

        if resp.status_code == 404:
            raise NotFoundError(path)
        if resp.status_code >= 400:
            raise UpstreamError(f"1C returned {resp.status_code}: {resp.text[:300]}")

        payload = resp.json()
        # Defensive: detect legacy MCBP_Exchange shape if someone points us at it.
        if isinstance(payload, dict) and payload.get("success") is False:
            blob = payload.get("data") or payload.get("answer") or payload.get("error") or ""
            if isinstance(blob, str) and blob:
                raise _classify_legacy_error(blob)
        return payload

    # --- High-level methods (the surface the rest of the app uses) ---
    async def health(self) -> dict:
        return await self._request("GET", "/ai/v1/health")

    async def list_catalog(self, type_: str, cursor: str | None, limit: int, q: str | None) -> dict:
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        if q:
            params["q"] = q
        return await self._request("GET", f"/ai/v1/catalogs/{type_}", params=params)

    async def list_documents(self, type_: str, frm: str | None, to: str | None,
                             cursor: str | None, limit: int) -> dict:
        params: dict[str, Any] = {"limit": limit}
        if frm:
            params["from"] = frm
        if to:
            params["to"] = to
        if cursor:
            params["cursor"] = cursor
        return await self._request("GET", f"/ai/v1/documents/{type_}", params=params)

    async def document_schema(self, type_: str) -> dict:
        return await self._request("GET", f"/ai/v1/documents/{type_}/schema")

    async def create_object(self, type_: str, body: dict, information_base: str) -> dict:
        return await self._request(
            "POST", f"/ai/v1/objects/{type_}",
            params={"InformationBase": information_base}, json=body,
        )

    async def register_balance(self, type_: str, filters: dict) -> dict:
        return await self._request("GET", f"/ai/v1/registers/{type_}/balance", params=filters)

    async def push_ai_context(self, body: dict) -> dict:
        return await self._request("POST", "/ai/v1/ai/context", json=body)


# --- Mock data so the backend boots and the AI loop is testable without 1C ---
# Форма навмисно повторює реальний зріз demo-бази basmbdemo (українська типова):
# кириличні типи (Контрагенты / ЗаказПокупателя), латинізовані ключі полів,
# посилання як {Presentation, Data, Metadata}, курсор = UUID останнього запису.
def _mock_response(method: str, path: str, kw: dict) -> Any:
    if path.endswith("/health"):
        return {"status": "ok", "service": "MCBP_AI", "key": True, "mock": True}
    if "/ai/context" in path:
        return {"accepted": True, "conversation_id": "mock-conv"}
    if "/catalogs/" in path:
        return {
            "data": [
                {"Kod": "000000001", "Naimenovanie": "Фурнітура південь, ТОВ",
                 "KodPoEDRPOU": "439857948579", "Postavshchik": "true", "Pokupatel": "false"},
                {"Kod": "000000002", "Naimenovanie": "Альфа Трейд, ТОВ",
                 "KodPoEDRPOU": "314159265", "Postavshchik": "false", "Pokupatel": "true"},
            ],
            "cursor": None,
        }
    if "/documents/" in path and path.endswith("/schema"):
        return {
            "type": path.split("/")[-2],
            "metadata": "document",
            "fields": [
                {"name": "Nomer", "synonym": "Номер"},
                {"name": "Data", "synonym": "Дата"},
                {"name": "Kontragent", "synonym": "Контрагент"},
                {"name": "SummaDokumenta", "synonym": "Сума документа"},
            ],
        }
    if "/documents/" in path:
        return {
            "data": [
                {"Nomer": "ЗП-00001", "Data": "2026-05-04T00:00:00", "SummaDokumenta": 15400.0},
                {"Nomer": "ЗП-00002", "Data": "2026-05-18T00:00:00", "SummaDokumenta": 8200.0},
            ],
            "cursor": None,
        }
    if "/registers/" in path and path.endswith("/balance"):
        return {"type": path.split("/")[-2], "data": {"balance": 6200.0, "currency": "UAH"}}
    if method == "POST" and "/objects/" in path:
        return {"type": path.split("/")[-1], "data": {"ref": "new-ref-001", "created": True}}
    return {"data": None}
