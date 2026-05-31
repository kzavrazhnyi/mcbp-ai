"""Конфігурація backend (читається з .env / оточення).

Іменування env-змінних:
  • MCBP-специфічні — з префіксом MCBP_ (MCBP_ONEC_MOCK, MCBP_LLM_PROVIDER, ...)
  • ключі моделей — стандартні ANTHROPIC_API_KEY / OPENAI_API_KEY (щоб їх підхоплював
    і SDK), з MCBP_-аліасом як запасним варіантом.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # App
    app_name: str = "mcbp-ai-backend"
    env: Literal["dev", "prod"] = Field("dev", validation_alias="MCBP_ENV")
    log_level: str = Field("INFO", validation_alias="MCBP_LOG_LEVEL")

    # 1С / MCBP_AI
    onec_mock: bool = Field(True, validation_alias="MCBP_ONEC_MOCK")
    onec_base_url: str = Field("http://localhost/base/hs", validation_alias="MCBP_ONEC_BASE_URL")
    onec_user: str = Field("", validation_alias="MCBP_ONEC_USER")
    onec_password: str = Field("", validation_alias="MCBP_ONEC_PASSWORD")
    onec_timeout_s: float = Field(30.0, validation_alias="MCBP_ONEC_TIMEOUT_S")
    onec_pool_max: int = Field(10, validation_alias="MCBP_ONEC_POOL_MAX")

    # LLM
    llm_provider: Literal["mock", "anthropic", "openai"] = Field(
        "mock", validation_alias="MCBP_LLM_PROVIDER"
    )
    anthropic_api_key: str = Field(
        "", validation_alias=AliasChoices("ANTHROPIC_API_KEY", "MCBP_ANTHROPIC_API_KEY")
    )
    anthropic_model: str = Field("claude-opus-4-8", validation_alias="MCBP_ANTHROPIC_MODEL")
    openai_api_key: str = Field(
        "", validation_alias=AliasChoices("OPENAI_API_KEY", "MCBP_OPENAI_API_KEY")
    )
    openai_model: str = Field("gpt-4o", validation_alias="MCBP_OPENAI_MODEL")
    llm_max_tool_iterations: int = Field(8, validation_alias="MCBP_LLM_MAX_TOOL_ITERATIONS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
