"""Shared LiteLLM/OpenAI-compatible client for the LLM-backed tooling
(autotag.py, summarize.py).

Config is read via pydantic-settings (typed, validated at construction):
  * LITELLM_BASE_URL  (default the homelab pikellm proxy, OpenAI-compatible)
  * LITELLM_API_KEY   (required; also accepts OPENAI_API_KEY / LITELLM_GATEWAY_KEY)
  * PUBLICATIONS_MODEL (default deepseek-v4-pro-cloud)

Construct Settings() only once you actually have model work to do, so a no-op
run (e.g. autotag with nothing untagged) needs no key.
"""

from __future__ import annotations

import httpx
from pydantic import AliasChoices, Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    litellm_base_url: HttpUrl = Field(default="http://127.0.0.1:4000/v1")
    litellm_api_key: SecretStr = Field(
        validation_alias=AliasChoices(
            "LITELLM_API_KEY", "OPENAI_API_KEY", "LITELLM_GATEWAY_KEY",
            "AUDIT_SKILLS_PIKELLM_KEY",
        )
    )
    model: str = Field(default="deepseek-v4-pro-cloud", validation_alias="PUBLICATIONS_MODEL")


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
    url = str(settings.litellm_base_url).rstrip("/") + "/chat/completions"
    resp = httpx.post(
        url,
        headers={"Authorization": f"Bearer {settings.litellm_api_key.get_secret_value()}"},
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
