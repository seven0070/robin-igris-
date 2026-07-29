"""Thin client helpers for Hermes Agent API server."""

from __future__ import annotations

import os
from typing import Any

import httpx


def hermes_base() -> str:
    return os.getenv("HERMES_BASE_URL", "http://127.0.0.1:8642/v1").rstrip("/")


def hermes_key() -> str:
    return os.getenv("HERMES_API_KEY", "robin-igris-dev")


def chat(
    messages: list[dict[str, Any]],
    *,
    model: str = "hermes-agent",
    session_key: str = "robin-igris",
    timeout: float = 120.0,
) -> str:
    """POST /v1/chat/completions against a running Hermes gateway API server."""
    headers = {
        "Authorization": f"Bearer {hermes_key()}",
        "Content-Type": "application/json",
        "X-Hermes-Session-Key": session_key,
    }
    payload = {"model": model, "messages": messages}
    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{hermes_base()}/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""


def health(timeout: float = 5.0) -> bool:
    base = hermes_base().removesuffix("/v1")
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(
                f"{base}/health",
                headers={"Authorization": f"Bearer {hermes_key()}"},
            )
            return r.is_success
    except Exception:  # noqa: BLE001
        return False
