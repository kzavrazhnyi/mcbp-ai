# 1C BAS MCBP+ Tool Contract

Canonical source — every other file references this; never restate these facts elsewhere.

The 6 data-fetch tools exposed by the `MCBP_AI` HTTP service. Full HTTP contract (request/response
shapes, auth, error codes, mock mode) lives in `mcbp-onec-integration` skill; this file is the
quick-reference index agents use before calling into that skill.

Source documents: `BACKEND_TECHNICAL.md`, `ANALYSIS_REPORT.md`, `BAS_CODE_MAP.md`.

## The 6 Tools

| Tool | Purpose | Endpoint |
|---|---|---|
| `search_catalog` | Full-text search in 1C catalog (items, goods, services) | POST /mcbp_ai/catalog/search |
| `get_documents` | Fetch business documents by filter (invoices, orders, acts) | POST /mcbp_ai/documents/list |
| `get_register_balance` | Account/accumulation register balance query | POST /mcbp_ai/registers/balance |
| `filter_catalog` | Filtered catalog query with structured predicates | POST /mcbp_ai/catalog/filter |
| `list_metadata` | List available metadata objects (catalogs, documents, registers) | GET /mcbp_ai/metadata/list |
| `describe_metadata` | Describe fields/structure of a specific metadata object | GET /mcbp_ai/metadata/{name} |

**Auth:** HTTP Basic (`MCBP_ONEC_USER` / `MCBP_ONEC_PASSWORD`) on every request — no session tokens.

**Retry:** 503 → retry 2× with backoff (`httpx.AsyncHTTPTransport(retries=2)`). 400/401/404 → no retry.

**Full request/response shapes:** see `.claude_dev/skills/mcbp-onec-integration/SKILL.md`.

## Trigger phrases (UA)

контракт інструментів, 1с контракт, 6 інструментів, mcbp_ai ендпоінти, tool contract,
search_catalog endpoint, get_documents endpoint, register balance endpoint.
