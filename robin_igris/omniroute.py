"""OmniRoute — primary LLM gateway for Robin Igris / PNAOS.

https://github.com/diegosouzapw/OmniRoute

OpenAI-compatible endpoint (default): http://127.0.0.1:20128/v1
Routing is offline-first: local model when no network / low budget;
cloud spillover via OmniRoute ``auto`` (or task aliases) when online.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from robin_igris.routing import RouteDecision, resolve_route

DEFAULT_BASE = "http://127.0.0.1:20128/v1"
DEFAULT_MODEL = "auto"
DEFAULT_KEY = "omniroute"


def base_url() -> str:
    return (
        os.getenv("OMNIROUTE_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or DEFAULT_BASE
    ).rstrip("/")


def api_key() -> str:
    return (
        os.getenv("OMNIROUTE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or DEFAULT_KEY
    )


def model() -> str:
    return os.getenv("OMNIROUTE_MODEL") or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL


def dashboard_url() -> str:
    root = base_url().removesuffix("/v1")
    return os.getenv("OMNIROUTE_DASHBOARD_URL", root)


def health(timeout: float = 3.0) -> bool:
    """True if OmniRoute answers /v1/models or dashboard health."""
    root = base_url().removesuffix("/v1")
    headers = {"Authorization": f"Bearer {api_key()}"}
    try:
        with httpx.Client(timeout=timeout) as client:
            for url in (
                f"{base_url()}/models",
                f"{root}/api/monitoring/health",
                f"{root}/health",
            ):
                try:
                    r = client.get(url, headers=headers)
                    if r.is_success:
                        return True
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        return False
    return False


def chat_text(
    messages: list[dict[str, Any]],
    *,
    model_name: str | None = None,
    temperature: float = 0.4,
    timeout: float = 120.0,
    route: RouteDecision | None = None,
    has_network: bool | None = None,
) -> str:
    """Chat completions via OmniRoute, optionally with a RouteDecision."""
    if model_name is None:
        if route is not None:
            model_name = route.model
        elif has_network is not None:
            user = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    user = str(m.get("content") or "")
                    break
            model_name = resolve_route(has_network=has_network, user_text=user).model
        else:
            model_name = model()

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{base_url()}/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
