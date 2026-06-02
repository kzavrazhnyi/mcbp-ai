"""Дані-проксі: дзеркалить контракт MCBP_AI для прямого доступу фронтенду/інтеграцій.

Кожен ендпоінт делегує в MCBPClient (mock або http) і повертає нормалізоване тіло.
Типізовані MCBPError перетворюються на коректні HTTP-коди обробником у main.py.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Query, Request

from app.core.deps import get_mcbp

router = APIRouter()


@router.get("/v1/catalogs/{type_}")
async def list_catalog(
    type_: str,
    q: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    fields: str | None = Query(None),
) -> dict:
    return await get_mcbp().list_catalog(type_, cursor, limit, q, fields)


@router.get("/v1/documents/{type_}/schema")
async def document_schema(type_: str) -> dict:
    return await get_mcbp().document_schema(type_)


@router.get("/v1/documents/{type_}")
async def list_documents(
    type_: str,
    request: Request,
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    fields: str | None = Query(None),
) -> dict:
    # Field filters arrive as f.<field>=<value> (e.g. f.Контрагент=<uuid>), mirroring MCBP_AI.
    filters = {k[2:]: v for k, v in request.query_params.items()
               if k.startswith("f.") and len(k) > 2}
    return await get_mcbp().list_documents(type_, from_, to, cursor, limit, filters, fields)


@router.post("/v1/objects/{type_}")
async def create_object(
    type_: str,
    information_base: str = Query(..., alias="InformationBase"),
    body: dict = Body(...),
) -> dict:
    return await get_mcbp().create_object(type_, body, information_base)


@router.get("/v1/registers/{type_}/balance")
async def register_balance(type_: str, request: Request) -> dict:
    filters = dict(request.query_params)
    return await get_mcbp().register_balance(type_, filters)
