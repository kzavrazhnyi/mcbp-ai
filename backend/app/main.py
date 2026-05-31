"""mcbp-ai-backend entrypoint.

Mount layout (everything under /ai to mirror the 1C service namespace):
  /ai/v1/health, /ai/v1/auth/token          (system)
  /ai/v1/catalogs|documents|objects|registers (data)
  /ai/v1/ai/query                             (model-driven AI)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.deps import container
from app.core.errors import MCBPError
from app.routers import ai, data, system

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

settings = get_settings()
logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await container.startup()
    yield
    await container.shutdown()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.env == "dev" else [],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(MCBPError)
async def mcbp_error_handler(_: Request, exc: MCBPError):
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


app.include_router(system.router, prefix="/ai")
app.include_router(data.router, prefix="/ai")
app.include_router(ai.router, prefix="/ai")


@app.get("/")
async def root():
    # Кореневий шлях веде на UI, якщо фронтенд присутній; інакше — інфо-JSON.
    if FRONTEND_DIR.is_dir():
        return RedirectResponse(url="/ui/")
    return {"service": settings.app_name, "docs": "/docs", "mock_1c": settings.onec_mock}


# Статичний фронтенд (HTML/JS/CSS). html=True віддає index.html на /ui/.
if FRONTEND_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")
