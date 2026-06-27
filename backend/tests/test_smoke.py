"""Smoke-тести у mock-режимі: backend піднімається й проганяє tool-loop без 1С і без ключів."""

import asyncio

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.clients.mcbp import MCBPClient, _classify_legacy_error
from app.core.config import Settings
from app.core.errors import KeyMismatchError, ParameterError, PlusRequiredError, UpstreamError
from app.main import app
from app.services.ai_orchestrator import SYSTEM_PROMPT


def test_health():
    with TestClient(app) as c:
        r = c.get("/ai/v1/health")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["backend"] == "ok"
        assert d["mock_1c"] is True


def test_catalog():
    with TestClient(app) as c:
        r = c.get("/ai/v1/catalogs/Контрагенты", params={"q": "ТОВ"})
        assert r.status_code == 200
        assert r.json()["data"]


def test_document_schema():
    with TestClient(app) as c:
        r = c.get("/ai/v1/documents/SalesOrder/schema")
        assert r.status_code == 200
        assert r.json()["fields"]


def test_ai_query_mock_drives_tool_loop():
    with TestClient(app) as c:
        r = c.post("/ai/v1/ai/query", json={"message": "Скільки контрагентів?", "stream": False})
        assert r.status_code == 200
        data = r.json()["data"]
        assert "answer" in data
        assert any(tc["name"] == "search_catalog" for tc in data["tool_calls"])


def test_documents_filters_and_fields_forwarded():
    # filters (f.<field>) і fields мають доходити до клієнта; mock відбиває fields у рядку.
    with TestClient(app) as c:
        r = c.get("/ai/v1/documents/ЗаказПокупателя",
                  params={"from": "2025-01-01", "to": "2026-06-02",
                          "f.Контрагент": "8e466903-ff05-11ef-a850-cc52afc9fc6f",
                          "fields": "Контрагент"})
        assert r.status_code == 200
        rows = r.json()["data"]
        assert rows and "Контрагент" in rows[0]


def test_success_false_is_raised_even_for_structured_detail():
    # 1С/Plus може повернути 200 з {success:false, data:...} — це має ставати помилкою, не «ok».
    settings = Settings(onec_mock=False, onec_base_url="http://test",
                        onec_user="u", onec_password="p")
    client = MCBPClient(settings)

    async def go():
        await client.startup()
        try:
            with respx.mock:
                respx.get("http://test/ai/v1/catalogs/X").mock(
                    return_value=httpx.Response(200, json={"success": False, "data": ""}))
                with pytest.raises(UpstreamError):
                    await client.list_catalog("X", None, 50, None)
        finally:
            await client.shutdown()

    asyncio.run(go())


def test_legacy_error_classification():
    assert isinstance(_classify_legacy_error("Key not found!"), KeyMismatchError)
    assert isinstance(_classify_legacy_error("MCBP Plus not found!"), PlusRequiredError)
    assert isinstance(_classify_legacy_error("Parameter type not found!"), ParameterError)


def test_metadata_all():
    with TestClient(app) as c:
        r = c.get("/ai/v1/metadata/all")
        assert r.status_code == 200
        j = r.json()
        assert "catalogs" in j


def test_get_object():
    with TestClient(app) as c:
        r = c.get("/ai/v1/object/Catalogs/Контрагенты/e3f1d9b6-0001-11ef-a850-cc52afc9fc6f")
        assert r.status_code == 200
        j = r.json()
        assert "data" in j


def test_metadata_describe():
    with TestClient(app) as c:
        r = c.get("/ai/v1/metadata/Catalogs/Контрагенты")
        assert r.status_code == 200
        j = r.json()
        assert "attributes" in j


def test_system_prompt_uses_bas_internal_names():
    # Промпт скеровує модель на ВНУТРІШНІ імена метаданих BAS (успадковані рос.), а не укр. синоніми.
    assert "BAS" in SYSTEM_PROMPT
    assert "Контрагенты" in SYSTEM_PROMPT
    assert "ЗаказПокупателя" in SYSTEM_PROMPT
    assert "Поставщик" in SYSTEM_PROMPT  # внутрішнє ім'я поля, не синонім «Постачальник»
