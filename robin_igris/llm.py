"""LLM client — OmniRoute gateway (OpenAI-compatible).

Primary backend: https://github.com/diegosouzapw/OmniRoute
Default: http://127.0.0.1:20128/v1  model=auto
"""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from robin_igris import omniroute


def get_client() -> OpenAI:
    return OpenAI(api_key=omniroute.api_key(), base_url=omniroute.base_url())


def get_model() -> str:
    return omniroute.model()


def chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    *,
    temperature: float = 0.4,
) -> Any:
    """Send a chat completion request via OmniRoute. Returns the message object."""
    client = get_client()
    kwargs: dict[str, Any] = {
        "model": get_model(),
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message
