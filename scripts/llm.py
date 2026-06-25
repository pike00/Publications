"""Shared OpenAI-compatible LLM client for the LLM-backed tooling
(autotag.py, summarize.py). Plain httpx against a /v1/chat/completions endpoint.

Config is read via pydantic-settings (typed, validated at construction) from the
environment and an optional repo-root `.env` file. See `.env.example`:
  * LLM_BASE_URL    OpenAI-compatible endpoint, include /v1 (default localhost:4000)
  * LLM_API_KEY     required; also read from OPENAI_API_KEY
  * LLM_MODEL       model id (default deepseek-v4-pro-cloud)

Construct LLMSettings() only once you actually have model work to do, so a no-op
run (e.g. autotag with nothing untagged) needs no key.
"""

from __future__ import annotations

import httpx
from pydantic import AliasChoices, Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_base_url: HttpUrl = Field(
        default="http://localhost:4000/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "LITELLM_BASE_URL", "OPENAI_BASE_URL"),
    )
    llm_api_key: SecretStr = Field(
        validation_alias=AliasChoices("LLM_API_KEY", "LITELLM_API_KEY", "OPENAI_API_KEY")
    )
    model: str = Field(
        default="deepseek-v4-pro-cloud",
        validation_alias=AliasChoices("LLM_MODEL", "PUBLICATIONS_MODEL"),
    )


def chat(
    settings: LLMSettings,
    system: str,
    user: str,
    *,
    max_tokens: int = 1024,
    temperature: float = 0.3,
    timeout: float = 120.0,
) -> str:
    """One chat completion; returns the assistant message content."""
    url = str(settings.llm_base_url).rstrip("/") + "/chat/completions"
    resp = httpx.post(
        url,
        headers={"Authorization": f"Bearer {settings.llm_api_key.get_secret_value()}"},
        json={
            "model": settings.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()
