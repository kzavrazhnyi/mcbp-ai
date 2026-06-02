"""Централізоване логування: консоль + ротаційний файл.

Мета — мати збережений слід того, **як ШІ працює з API**: вхідний HTTP-запит →
які інструменти обрала модель (tool_call) → які виклики пішли в 1С (mcbp.api) →
їхні статуси/час → фінальна відповідь. Файл можна переглядати постфактум.

Логери за призначенням:
  mcbp.http  — вхідні HTTP-запити до backend
  mcbp.ai    — кроки tool-loop оркестратора (запит, tool_call, tool_result, answer)
  mcbp.api   — вихідні запити до 1С MCBP_AI (метод, шлях, статус, мс)
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import Settings

# backend/logs/mcbp_ai.log  (backend = тека на два рівні вище за цей файл: app/core/..)
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "mcbp_ai.log"

_FMT = "%(asctime)s %(levelname)-5s %(name)-12s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"
_configured = False


def setup_logging(settings: Settings) -> Path:
    """Налаштовує root-логер (консоль + ротаційний файл). Ідемпотентно."""
    global _configured

    root = logging.getLogger()
    root.setLevel(getattr(logging, str(settings.log_level).upper(), logging.INFO))

    if not _configured:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        formatter = logging.Formatter(_FMT, datefmt=_DATEFMT)

        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

        # watchfiles (uvicorn --reload) інакше спамить "change detected" на кожен
        # запис у лог-файл → петля. Лишаємо лише попередження.
        logging.getLogger("watchfiles").setLevel(logging.WARNING)

        _configured = True

    return LOG_FILE
