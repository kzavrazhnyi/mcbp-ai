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
import logging
import time
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


log = logging.getLogger("mcbp.api")


def _classify_legacy_error(text: str) -> Exception:
    for marker, exc in _ERROR_MARKERS:
        if marker.lower() in text.lower():
            return exc(text)
    return UpstreamError(text)


def _kw_brief(kw: dict) -> str:
    """Короткий опис параметрів запиту для лога (без зайвого тіла)."""
    parts = []
    if kw.get("params"):
        parts.append(f"params={kw['params']}")
    body = kw.get("json")
    if body is not None:
        keys = list(body.keys()) if isinstance(body, dict) else type(body).__name__
        parts.append(f"body_keys={keys}")
    return " ".join(parts)


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
        brief = _kw_brief(kw)
        if self._mock:
            log.info("[mock] %s %s %s", method, path, brief)
            return _mock_response(method, path, kw)
        assert self._client is not None, "MCBPClient.startup() not called"

        start = time.monotonic()
        try:
            resp = await self._client.request(method, path, **kw)
        except httpx.HTTPError as e:
            log.warning("%s %s %s ✗ transport error: %s", method, path, brief, e)
            raise UpstreamError(f"transport error: {e}") from e

        elapsed_ms = (time.monotonic() - start) * 1000
        log.info("%s %s %s → %s (%.0f ms)", method, path, brief, resp.status_code, elapsed_ms)

        if resp.status_code == 404:
            raise NotFoundError(path)
        if resp.status_code >= 400:
            raise UpstreamError(f"1C returned {resp.status_code}: {resp.text[:300]}")

        payload = resp.json()
        # Defensive: detect the "success:false" failure shape (legacy MCBP_Exchange, or a Plus
        # call that returns 200 with {success:false, data:...}). Raise regardless of whether the
        # detail is a string or a structure, so a failed result never passes as a valid answer.
        if isinstance(payload, dict) and payload.get("success") is False:
            blob = payload.get("data") or payload.get("answer") or payload.get("error")
            if isinstance(blob, str) and blob:
                raise _classify_legacy_error(blob)
            raise UpstreamError(f"upstream reported success=false: {str(blob)[:200]}")
        return payload

    # --- High-level methods (the surface the rest of the app uses) ---
    async def health(self) -> dict:
        return await self._request("GET", "/ai/v1/health")

    async def list_catalog(self, type_: str, cursor: str | None, limit: int, q: str | None,
                           fields: list | str | None = None) -> dict:
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        if q:
            params["q"] = q
        if fields:
            params["fields"] = ",".join(fields) if isinstance(fields, list) else fields
        return await self._request("GET", f"/ai/v1/catalogs/{type_}", params=params)

    async def filter_catalog(self, type_: str, filters: dict | None, orderby: str | None,
                             desc: bool, exclude_groups: bool, limit: int,
                             cursor: str | None = None, fields: list | str | None = None) -> dict:
        """Server-side filter by ANY field (+optional sort / group-exclusion). Field names
        are the real metadata names (from describe_metadata); filtering/typing happens in 1C.
        Reference fields are filtered by passing the object's Ref UUID as the value."""
        params: dict[str, Any] = {"limit": limit}
        for k, v in (filters or {}).items():
            params[f"f.{k}"] = v  # 'f.' prefix keeps filters separate from reserved params
        if orderby:
            params["orderby"] = orderby
        if desc:
            params["desc"] = "true"
        if exclude_groups:
            params["excludeGroups"] = "true"
        if cursor:
            params["cursor"] = cursor
        if fields:
            params["fields"] = ",".join(fields) if isinstance(fields, list) else fields
        return await self._request("GET", f"/ai/v1/catalogs/{type_}", params=params)

    async def list_documents(self, type_: str, frm: str | None, to: str | None,
                             cursor: str | None, limit: int,
                             filters: dict | None = None, fields: list | str | None = None) -> dict:
        """Documents of a type over a period, with optional server-side field filters
        (incl. reference fields, e.g. {"Контрагент": "<uuid>"}) and extra header fields
        returned in each row (e.g. ["Контрагент", "СуммаДокумента"])."""
        params: dict[str, Any] = {"limit": limit}
        if frm:
            params["from"] = frm
        if to:
            params["to"] = to
        if cursor:
            params["cursor"] = cursor
        for k, v in (filters or {}).items():
            params[f"f.{k}"] = v  # 'f.' prefix keeps filters separate from reserved params
        if fields:
            params["fields"] = ",".join(fields) if isinstance(fields, list) else fields
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

    # --- Configuration introspection (works for ANY 1C configuration) ---
    async def list_metadata(self, kind: str) -> dict:
        """kind='all' → object lists of every kind; kind='Catalogs'/'Documents'/... → list of one kind."""
        return await self._request("GET", f"/ai/v1/metadata/{kind}")

    async def describe_metadata(self, kind: str, type_: str) -> dict:
        """Full attribute/tabular-section tree of one metadata object."""
        return await self._request("GET", f"/ai/v1/metadata/{kind}/{type_}")

    async def get_object(self, kind: str, type_: str, object_id: str) -> dict:
        """FULL data of one object (all attributes + tabular sections) by its Ref UUID.
        Lists return only standard fields; this is the drill-down for a specific record."""
        return await self._request("GET", f"/ai/v1/object/{kind}/{type_}/{object_id}")


# --- Mock data so the backend boots and the AI loop is testable without 1C ---
# Форма навмисно повторює реальний зріз demo-бази basmbdemo (українська типова):
# кириличні типи (Контрагенты / ЗаказПокупателя), латинізовані ключі полів,
# посилання як {Presentation, Data, Metadata}, курсор = UUID останнього запису.
def _mock_extra_fields(kw: dict) -> dict:
    """Echo the requested `fields` back into a mock row, so callers/tests can see they were sent."""
    fields = (kw.get("params") or {}).get("fields")
    if not fields:
        return {}
    names = fields.split(",") if isinstance(fields, str) else fields
    return {name.strip(): f"<mock:{name.strip()}>" for name in names if name and name.strip()}


def _mock_response(method: str, path: str, kw: dict) -> Any:
    if path.endswith("/health"):
        return {"status": "ok", "service": "MCBP_AI", "key": True, "mock": True}
    if "/metadata/" in path:
        return _mock_metadata(path)
    if "/ai/v1/object/" in path:  # singular: full data of one object
        return {"metadata": "catalog", "type": path.split("/")[-2],
                "data": [{"Kod": "000000002"}, {"Naimenovanie": "Альфа Трейд, ТОВ"},
                         {"Pokupatel": "true"}, {"KodPoEDRPOU": "314159265"}]}
    if "/ai/context" in path:
        return {"accepted": True, "conversation_id": "mock-conv"}
    if "/catalogs/" in path:
        # Compact: standard attributes only (canonical English keys) + Ref for drill-down,
        # plus any requested `fields` (echoed so tests can assert they were forwarded).
        rows = [
            {"Ref": {"Presentation": "Фурнітура південь, ТОВ", "Data": "e3f1d9b6-0001",
                     "Metadata": "Контрагенты"}, "Code": "000000001",
             "Description": "Фурнітура південь, ТОВ", "DeletionMark": False, "IsFolder": False},
            {"Ref": {"Presentation": "Альфа Трейд, ТОВ", "Data": "e3f1d9b6-0002",
                     "Metadata": "Контрагенты"}, "Code": "000000002",
             "Description": "Альфа Трейд, ТОВ", "DeletionMark": False, "IsFolder": False},
        ]
        for row in rows:
            row.update(_mock_extra_fields(kw))
        return {"data": rows, "cursor": None}
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
        # Compact: standard document fields only (Number/Date/Posted/...) + Ref,
        # plus any requested `fields` (echoed so tests can assert they were forwarded).
        rows = [
            {"Ref": {"Presentation": "ЗП-00001", "Data": "doc-0001", "Metadata": "ЗаказПокупателя"},
             "Number": "ЗП-00001", "Date": "2026-05-04 00:00:00", "Posted": True, "DeletionMark": False},
            {"Ref": {"Presentation": "ЗП-00002", "Data": "doc-0002", "Metadata": "ЗаказПокупателя"},
             "Number": "ЗП-00002", "Date": "2026-05-18 00:00:00", "Posted": True, "DeletionMark": False},
        ]
        for row in rows:
            row.update(_mock_extra_fields(kw))
        return {"data": rows, "cursor": None}
    if "/registers/" in path and path.endswith("/balance"):
        return {"type": path.split("/")[-2], "data": {"balance": 6200.0, "currency": "UAH"}}
    if method == "POST" and "/objects/" in path:
        return {"type": path.split("/")[-1], "data": {"ref": "new-ref-001", "created": True}}
    return {"data": None}


# Mock для інтроспекції структури — форма повторює реальний ai_metadata_get.
def _mock_metadata(path: str) -> Any:
    tail = path.split("/metadata/", 1)[1]
    parts = [p for p in tail.split("/") if p]
    if parts and parts[0].lower() == "all":
        return {
            "catalogs": [{"name": "Контрагенты", "synonym": "Контрагенти"},
                         {"name": "Номенклатура", "synonym": "Номенклатура"}],
            "documents": [{"name": "ЗаказПокупателя", "synonym": "Замовлення покупця"}],
            "informationregisters": [{"name": "MCBP_StatusFunctions", "synonym": "Статус функцій"}],
        }
    if len(parts) == 1:
        return {"metadata": parts[0].lower(), "count": 2,
                "items": [{"name": "Контрагенты", "synonym": "Контрагенти"},
                          {"name": "Номенклатура", "synonym": "Номенклатура"}]}
    # detail
    return {
        "metadata": "catalog", "type": parts[1], "synonym": "Контрагенти",
        "standard_attributes": [
            {"name": "Naimenovanie", "synonym": "Найменування", "types": ["Рядок"], "length": 100},
            {"name": "Kod", "synonym": "Код", "types": ["Рядок"], "length": 11},
        ],
        "attributes": [
            {"name": "Pokupatel", "synonym": "Покупець", "types": ["Булево"]},
            {"name": "Postavshchik", "synonym": "Постачальник", "types": ["Булево"]},
            {"name": "KodPoEDRPOU", "synonym": "Код за ЄДРПОУ", "types": ["Рядок"], "length": 10},
        ],
        "tabular_sections": [],
    }
