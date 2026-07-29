"""Grok Build tools — Manifest-gated coding sidecar."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from robin_igris.grok_build.client import GrokBuildClient


def _ok(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _err(msg: str, **extra: Any) -> str:
    return json.dumps({"error": msg, **extra}, ensure_ascii=False)


def _client() -> GrokBuildClient:
    return GrokBuildClient.detect()


def _cwd() -> Path:
    root = os.getenv("ROBIN_USB_ROOT") or os.getenv("AOS_USB_ROOT")
    if root:
        app = Path(root) / "app"
        return app if app.exists() else Path(root)
    return Path.cwd()


def grok_status() -> str:
    return _ok(_client().status())


def grok_ask(prompt: str, cwd: str = "", output_format: str = "plain") -> str:
    """Headless grok -p — coding / codebase tasks."""
    c = _client()
    work = Path(cwd) if cwd else _cwd()
    return _ok(
        c.run_headless(
            prompt,
            cwd=work,
            output_format=output_format if output_format in {"plain", "json"} else "plain",
        )
    )


def grok_code(task: str, cwd: str = "", yolo: bool = False) -> str:
    """Coding-focused headless run (preferred for refactor/bugfix)."""
    c = _client()
    work = Path(cwd) if cwd else _cwd()
    return _ok(
        c.run_headless(
            task,
            cwd=work,
            output_format="plain",
            yolo=yolo or os.getenv("ROBIN_GROK_YOLO", "0") == "1",
            model=os.getenv("ROBIN_GROK_MODEL") or "grok-build",
        )
    )


TOOL_IMPLS: dict[str, Callable[..., str]] = {
    "grok_status": grok_status,
    "grok_ask": grok_ask,
    "grok_code": grok_code,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "grok_status",
            "description": "Check if Grok Build (xai-org/grok-build) CLI is installed and ready.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grok_ask",
            "description": "Run Grok Build headless (grok -p) for a coding/codebase prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "cwd": {"type": "string"},
                    "output_format": {"type": "string", "default": "plain"},
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grok_code",
            "description": "Ask Grok Build to perform a coding task (refactor, bugfix, implement).",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "cwd": {"type": "string"},
                    "yolo": {"type": "boolean", "default": False},
                },
                "required": ["task"],
            },
        },
    },
]
