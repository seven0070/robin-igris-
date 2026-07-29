"""Manifest-scoped Buzz.xyz tools for Robin Igris / PNAOS.

Tools are the Semantic Boundary Gateway: the agent never holds raw network
sockets for Buzz — only these named operations, gated by AgenticOS Manifest
capability ``buzz`` (and optionally finer ``buzz_*`` flags).
"""

from __future__ import annotations

import json
from typing import Any, Callable

from robin_igris.buzz.client import BuzzClient, BuzzError


def _client() -> BuzzClient:
    return BuzzClient()


def _ok(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _err(exc: Exception) -> str:
    if isinstance(exc, BuzzError):
        return json.dumps(
            {"error": str(exc), "exit_code": exc.exit_code, "raw": exc.raw[:500]},
            ensure_ascii=False,
        )
    return json.dumps({"error": str(exc)})


def buzz_status() -> str:
    """Check Buzz CLI + env configuration (no network write)."""
    return _ok(_client().status())


def buzz_list_channels() -> str:
    """List Buzz channels the agent can see."""
    try:
        return _ok(_client().list_channels())
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def buzz_list_tasks(channel: str | None = None, limit: int = 20) -> str:
    """Read recent channel messages / assigned work (tasks live in the room)."""
    try:
        return _ok(_client().list_messages(channel=channel or None, limit=int(limit)))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def buzz_read_thread(event_id: str, channel: str | None = None) -> str:
    """Read a conversation thread by root/event id."""
    try:
        return _ok(_client().read_thread(event_id, channel=channel or None))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def buzz_send_message(
    content: str,
    channel: str | None = None,
    reply_to: str | None = None,
) -> str:
    """Post a message (or task update) to a Buzz channel."""
    try:
        return _ok(
            _client().send_message(
                content,
                channel=channel or None,
                reply_to=reply_to or None,
            )
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def buzz_complete_task(
    content: str,
    channel: str | None = None,
    reply_to: str | None = None,
) -> str:
    """Mark work done by posting a completion message with outputs."""
    body = content if content.strip().lower().startswith("done") else f"Done — {content}"
    return buzz_send_message(body, channel=channel, reply_to=reply_to)


def buzz_upload_artifact(path: str) -> str:
    """Upload a file artifact to the Buzz Blossom store."""
    try:
        return _ok(_client().upload_artifact(path))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def buzz_request_human_input(
    question: str,
    channel: str | None = None,
    mention: str | None = None,
) -> str:
    """Ask the human teammate for clarification in the shared workspace."""
    try:
        return _ok(
            _client().request_human_input(
                question,
                channel=channel or None,
                mention=mention or None,
            )
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def buzz_search(query: str) -> str:
    """Search shared workspace history."""
    try:
        return _ok(_client().search(query))
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def buzz_feed() -> str:
    """Get activity feed (mentions, needs_action, etc.)."""
    try:
        return _ok(_client().feed())
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


TOOL_IMPLS: dict[str, Callable[..., str]] = {
    "buzz_status": buzz_status,
    "buzz_list_channels": buzz_list_channels,
    "buzz_list_tasks": buzz_list_tasks,
    "buzz_read_thread": buzz_read_thread,
    "buzz_send_message": buzz_send_message,
    "buzz_complete_task": buzz_complete_task,
    "buzz_upload_artifact": buzz_upload_artifact,
    "buzz_request_human_input": buzz_request_human_input,
    "buzz_search": buzz_search,
    "buzz_feed": buzz_feed,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "buzz_status",
            "description": "Check Buzz.xyz workspace CLI configuration and connectivity readiness.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buzz_list_channels",
            "description": "List Buzz channels in the shared human+agent workspace.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buzz_list_tasks",
            "description": "Read recent messages/tasks from a Buzz channel (shared workspace inbox).",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel UUID (optional if BUZZ_CHANNEL_ID set)"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buzz_read_thread",
            "description": "Read a Buzz message thread by event id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "channel": {"type": "string"},
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buzz_send_message",
            "description": "Send a message to a Buzz channel (human+agent shared workspace).",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "channel": {"type": "string"},
                    "reply_to": {"type": "string", "description": "Parent event id for threading"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buzz_complete_task",
            "description": "Post a task-completion update (with outputs) to Buzz.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "What was completed / outputs"},
                    "channel": {"type": "string"},
                    "reply_to": {"type": "string"},
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buzz_upload_artifact",
            "description": "Upload a local file artifact to Buzz (Blossom store).",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Absolute or relative file path"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buzz_request_human_input",
            "description": "Ask the human teammate a clarifying question in Buzz.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "channel": {"type": "string"},
                    "mention": {"type": "string", "description": "Exact full display name after @"},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buzz_search",
            "description": "Full-text search across the Buzz workspace history.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buzz_feed",
            "description": "Fetch Buzz activity feed (mentions, needs_action, activity).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
