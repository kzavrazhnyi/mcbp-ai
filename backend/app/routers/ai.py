"""ШІ-ендпоінт: модель сама маршрутизує дані 1С через tool-calling.

POST /ai/v1/ai/query
  body: { "message": str, "stream": bool, "allowed_tools": [str] | null }
  stream=false → JSON { data: { answer, tool_calls } }
  stream=true  → SSE-потік подій (tool_call / tool_result / answer)
"""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.deps import get_orchestrator

router = APIRouter()


class AIQueryRequest(BaseModel):
    message: str = Field(..., min_length=1)
    stream: bool = False
    allowed_tools: list[str] | None = None


@router.post("/v1/ai/query")
async def ai_query(req: AIQueryRequest):
    orch = get_orchestrator()

    if not req.stream:
        result = await orch.run(req.message, req.allowed_tools)
        return {"data": result}

    async def event_stream():
        async for event in orch.stream(req.message, req.allowed_tools):
            yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
