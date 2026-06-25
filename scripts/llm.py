"""Shared pydantic-ai client for the LLM-backed tooling (autotag.py, summarize.py).

Config is read via pydantic-settings (typed, validated at construction) from the
environment and an optional repo-root `.env` file. See `.env.example`:
  * LITELLM_BASE_URL    OpenAI-compatible endpoint (default: homelab pikellm proxy)
  * LITELLM_API_KEY     required; also read from OPENAI_API_KEY / LITELLM_GATEWAY_KEY
  * PUBLICATIONS_MODEL  model id (default: deepseek-v4-pro-cloud)

`build_agent()` returns a pydantic-ai Agent pointed at the configured endpoint.
Construct LLMSettings() only once you actually have model work to do, so a no-op
run (e.g. autotag with nothing untagged) needs no key.
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    litellm_base_url: HttpUrl = Field(default="http://127.0.0.1:4000/v1")
    litellm_api_key: SecretStr = Field(
        validation_alias=AliasChoices(
            "LITELLM_API_KEY", "OPENAI_API_KEY", "LITELLM_GATEWAY_KEY",
            "AUDIT_SKILLS_PIKELLM_KEY",
        )
    )
    model: str = Field(
        default="deepseek-v4-pro-cloud",
        validation_alias=AliasChoices("PUBLICATIONS_MODEL", "LITELLM_MODEL"),
    )


def build_model(settings: LLMSettings) -> OpenAIChatModel:
    return OpenAIChatModel(
        settings.model,
        provider=OpenAIProvider(
            base_url=str(settings.litellm_base_url),
            api_key=settings.litellm_api_key.get_secret_value(),
        ),
    )


def build_agent(settings: LLMSettings, *, instructions: str, output_type: Any = str) -> Agent:
    """A pydantic-ai Agent at the configured endpoint. output_type=str for free
    text; pass a Pydantic model for validated structured output."""
    return Agent(build_model(settings), instructions=instructions, output_type=output_type)
