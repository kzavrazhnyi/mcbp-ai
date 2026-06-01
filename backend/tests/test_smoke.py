"""Smoke-тести у mock-режимі: backend піднімається й проганяє tool-loop без 1С і без ключів."""

from fastapi.testclient import TestClient

from app.clients.mcbp import _classify_legacy_error
from app.core.errors import KeyMismatchError, ParameterError, PlusRequiredError
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


def test_legacy_error_classification():
    assert isinstance(_classify_legacy_error("Key not found!"), KeyMismatchError)
    assert isinstance(_classify_legacy_error("MCBP Plus not found!"), PlusRequiredError)
    assert isinstance(_classify_legacy_error("Parameter type not found!"), ParameterError)


def test_system_prompt_uses_russian_metadata_names():
    # Системний промпт — єдине, що скеровує модель на коректні (російські) імена типів 1С.
    assert "Контрагенты" in SYSTEM_PROMPT
    assert "ЗаказПокупателя" in SYSTEM_PROMPT
    assert "РОСІЙСЬКОМОВНІ" in SYSTEM_PROMPT
