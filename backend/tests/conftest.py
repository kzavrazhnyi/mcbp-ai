"""Ізоляція тестів від .env: примусово вмикаємо mock-режим до імпорту застосунку.

conftest збирається раніше за тестові модулі, тож env-змінні, виставлені тут на
рівні модуля, діють ще до того, як app.main викличе get_settings().
"""

import os

os.environ["MCBP_ONEC_MOCK"] = "true"
os.environ["MCBP_LLM_PROVIDER"] = "mock"

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()  # на випадок, якщо .env уже прочитали
