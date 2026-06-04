---
name: mcbp-onec-integration
description: "1C BAS MCBP+ HTTP service integration: the 6 tool request/response shapes, BAS metadata model, session auth, httpx retry strategy, MCBP+ error codes, and mock mode patterns. Use when working on backend/app/clients/mcbp.py or any code that calls the 1C MCBP_AI HTTP service. Trigger — EN: mcbp, 1c api, bas, onec, mcbp_ai, session auth, tool contract, error codes, mock mode. Trigger — UA: мцбп, 1с апі, бас, 1с, mcbp_ai, сесія авторизація, контракт інструменту, коди помилок, мок режим."
---

# 1C BAS MCBP+ HTTP Integration

Reference for the HTTP contract between mcbp-ai and the BAS MCBP_AI service.
Source documents: `BACKEND_TECHNICAL.md`, `ANALYSIS_REPORT.md`, `BAS_CODE_MAP.md`.

## Service Overview

The 1C BAS MCBP+ service exposes an HTTP API (called "MCBP_AI") that accepts JSON requests and returns JSON responses. It is a BAS (1C Business Automation Suite) application exposing ERP data via REST-like endpoints. The mcbp-ai backend calls these endpoints to fetch business data when the LLM requests a tool call.

## The 6 Tools — HTTP Contract

### 1. `search_catalog`

Full-text search across the 1C catalog (items, goods, services).

**Request:**
```json
POST /mcbp_ai/catalog/search
Authorization: Basic <base64(user:password)>
Content-Type: application/json

{
  "query": "string (required)",
  "limit": 10,
  "offset": 0
}
```

**Response:**
```json
{
  "items": [
    {"id": "string", "name": "string", "code": "string", "description": "string | null"}
  ],
  "total": 42
}
```

### 2. `get_documents`

Fetch business documents (invoices, orders, acts) matching a filter.

**Request:**
```json
POST /mcbp_ai/documents/list
{
  "document_type": "string (required)",
  "date_from": "YYYY-MM-DD | null",
  "date_to": "YYYY-MM-DD | null",
  "counterparty_id": "string | null",
  "limit": 20
}
```

**Response:**
```json
{
  "documents": [
    {"id": "string", "type": "string", "date": "YYYY-MM-DD", "number": "string", "amount": 0.0, "currency": "UAH"}
  ]
}
```

### 3. `get_register_balance`

Query account/accumulation register balance.

**Request:**
```json
POST /mcbp_ai/registers/balance
{
  "register_name": "string (required)",
  "date": "YYYY-MM-DD (required)",
  "dimensions": {"key": "value"}
}
```

**Response:**
```json
{
  "register": "string",
  "date": "YYYY-MM-DD",
  "balance": 0.0,
  "currency": "UAH",
  "dimensions": {}
}
```

### 4. `filter_catalog`

Filtered catalog query with structured predicates.

**Request:**
```json
POST /mcbp_ai/catalog/filter
{
  "catalog_name": "string (required)",
  "filters": [{"field": "string", "op": "eq|lt|gt|like", "value": "any"}],
  "limit": 20
}
```

**Response:**
```json
{"items": [...], "total": 0}
```

### 5. `list_metadata`

List available metadata objects (catalogs, documents, registers) in the 1C infobase.

**Request:**
```
GET /mcbp_ai/metadata/list
```

**Response:**
```json
{
  "catalogs": ["string"],
  "documents": ["string"],
  "registers": ["string"]
}
```

### 6. `describe_metadata`

Describe the fields and structure of a specific metadata object.

**Request:**
```
GET /mcbp_ai/metadata/{name}
```

**Response:**
```json
{
  "name": "string",
  "type": "Catalog|Document|Register",
  "fields": [
    {"name": "string", "type": "string", "required": true}
  ]
}
```

## Authentication

**HTTP Basic Auth** — `(MCBP_ONEC_USER, MCBP_ONEC_PASSWORD)` on every request.

```python
response = await self._client.post(
    url,
    json=payload,
    auth=(settings.mcbp_onec_user, settings.mcbp_onec_password),
)
```

Session tokens are NOT used — every request carries credentials. The 1C service validates per request.

## Error Codes

| HTTP Status | Meaning | Retry? |
|---|---|---|
| 200 | Success | — |
| 400 | Bad request (invalid filter, missing field) | No |
| 401 | Authentication failed — wrong user/password | No |
| 404 | Object not found (unknown catalog/document) | No |
| 503 | Service temporarily unavailable | Yes (2x, backoff) |
| 500 | 1C server error | Log + surface to user |

**Retry strategy for 503:**
```python
transport = httpx.AsyncHTTPTransport(retries=2)
async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
    ...
```

## BAS Metadata Model

BAS metadata objects follow the 1C standard hierarchy:

- **Catalogs** — reference data (counterparties, items, currencies, warehouses)
- **Documents** — transactional records (invoices, payments, shipments)
- **Accumulation Registers** — balance/turnover storage (stock, debt, cash)
- **Information Registers** — non-accumulative data (prices, exchange rates)

Use `list_metadata` to discover available objects; use `describe_metadata` to get field schemas before constructing queries.

## Mock Mode

When `settings.mock_mode = True`, `McbpClient` is replaced with `MockMcbpClient`:

```python
class MockMcbpClient:
    """Returns deterministic fixtures — no network calls."""

    async def search_catalog(self, query: str, limit: int = 10) -> CatalogSearchResult:
        return CatalogSearchResult(
            items=[CatalogItem(id="mock-001", name=f"Mock: {query}", code="MOCK")],
            total=1,
        )

    async def list_metadata(self) -> MetadataList:
        return MetadataList(
            catalogs=["Counterparties", "Products"],
            documents=["CustomerOrder", "Invoice"],
            registers=["GoodsStock", "MutualSettlements"],
        )
    # ... etc
```

Use `MockMcbpClient` in ALL tests — never call the real 1C service in tests.

## Common Mistakes

- Forgetting `raise_for_status()` — silent HTTP error passthrough.
- Creating `AsyncClient` per tool call instead of per lifespan.
- Returning raw `response.json()` dict instead of Pydantic model.
- Not handling 503 with retry — 1C BAS services restart periodically.
- Using synchronous `httpx.Client` — all calls must be async.

## References

- `BACKEND_TECHNICAL.md` — complete HTTP contract specification
- `ANALYSIS_REPORT.md` — analysis of MCBP+ HTTP behavior
- `BAS_CODE_MAP.md` — 1C method name → Python tool name mapping

## Trigger phrases (UA)

мцбп, 1с апі, бас, 1с, mcbp_ai, сесія авторизація, контракт інструменту, коди помилок, мок режим, search_catalog, get_documents, get_register_balance, filter_catalog, list_metadata, describe_metadata.
