"""Built-in tools for Robin Igris."""

from __future__ import annotations

import ast
import json
import math
import operator
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import quote_plus

import httpx

# Safe math for the calculator
_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "log10": math.log10,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
}
_CONSTS = {"pi": math.pi, "e": math.e}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name) and node.id in _CONSTS:
        return _CONSTS[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        if name not in _FUNCS:
            raise ValueError(f"Unknown function: {name}")
        return _FUNCS[name](*(_eval_node(a) for a in node.args))
    raise ValueError("Unsupported expression")


def calculator(expression: str) -> str:
    """Evaluate a math expression safely (e.g. '2 + 3 * sqrt(16)')."""
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        return str(_eval_node(tree))
    except Exception as exc:  # noqa: BLE001
        return f"Error: {exc}"


def get_current_time(timezone_name: str = "UTC") -> str:
    """Return the current time. timezone_name is informational; result is UTC ISO."""
    now = datetime.now(timezone.utc)
    return json.dumps(
        {
            "utc_iso": now.isoformat(),
            "unix": int(now.timestamp()),
            "requested_timezone": timezone_name,
            "note": "Value is UTC; convert locally as needed.",
        }
    )


def web_search(query: str, max_results: int = 5) -> str:
    """Search the web via DuckDuckGo Instant Answer / HTML lite results."""
    max_results = max(1, min(int(max_results), 8))
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            # Prefer Instant Answer API for structured snippets
            r = client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            r.raise_for_status()
            data = r.json()
            items: list[dict[str, str]] = []
            if data.get("AbstractText"):
                items.append(
                    {
                        "title": data.get("Heading") or query,
                        "snippet": data["AbstractText"],
                        "url": data.get("AbstractURL") or "",
                    }
                )
            for topic in data.get("RelatedTopics") or []:
                if len(items) >= max_results:
                    break
                if isinstance(topic, dict) and topic.get("Text"):
                    items.append(
                        {
                            "title": (topic.get("Text") or "")[:80],
                            "snippet": topic.get("Text") or "",
                            "url": topic.get("FirstURL") or "",
                        }
                    )
                elif isinstance(topic, dict) and "Topics" in topic:
                    for sub in topic["Topics"]:
                        if len(items) >= max_results:
                            break
                        if sub.get("Text"):
                            items.append(
                                {
                                    "title": (sub.get("Text") or "")[:80],
                                    "snippet": sub.get("Text") or "",
                                    "url": sub.get("FirstURL") or "",
                                }
                            )

            if not items:
                # Fallback: scrape lite HTML titles
                html = client.get(
                    f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
                )
                html.raise_for_status()
                text = html.text
                # Very small parser for result links
                import re

                for m in re.finditer(
                    r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                    text,
                    re.I | re.S,
                ):
                    if len(items) >= max_results:
                        break
                    url, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
                    items.append({"title": title, "snippet": title, "url": url})

            if not items:
                return json.dumps({"query": query, "results": [], "message": "No results."})
            return json.dumps({"query": query, "results": items}, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc), "query": query})


def remember_note(note: str) -> str:
    """Store a short note in the session scratchpad (in-memory)."""
    remember_note.notes.append(note.strip())  # type: ignore[attr-defined]
    return json.dumps({"stored": True, "count": len(remember_note.notes)})  # type: ignore[attr-defined]


remember_note.notes = []  # type: ignore[attr-defined]


def recall_notes() -> str:
    """Recall notes stored with remember_note in this session."""
    notes = getattr(remember_note, "notes", [])
    return json.dumps({"notes": notes, "count": len(notes)})


# Buzz.xyz shared workspace tools (Manifest-gated)
from robin_igris.buzz.tools import TOOL_IMPLS as _BUZZ_IMPLS  # noqa: E402
from robin_igris.buzz.tools import TOOL_SCHEMAS as _BUZZ_SCHEMAS  # noqa: E402


TOOL_IMPLS: dict[str, Callable[..., str]] = {
    "calculator": calculator,
    "get_current_time": get_current_time,
    "web_search": web_search,
    "remember_note": remember_note,
    "recall_notes": recall_notes,
    **_BUZZ_IMPLS,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a math expression. Supports +, -, *, /, **, sqrt, sin, cos, tan, log, pi, e.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate, e.g. 'sqrt(144) + 2**3'",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current UTC time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone_name": {
                        "type": "string",
                        "description": "Requested timezone label (informational).",
                        "default": "UTC",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {
                        "type": "integer",
                        "description": "Max results (1-8)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_note",
            "description": "Store a short note for later in this chat session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "note": {"type": "string", "description": "Text to remember"}
                },
                "required": ["note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_notes",
            "description": "Recall notes stored earlier in this session.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

TOOL_SCHEMAS.extend(_BUZZ_SCHEMAS)


def run_tool(name: str, arguments: dict[str, Any] | str) -> str:
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            arguments = {}
    if name.startswith("buzz_"):
        from robin_igris.buzz.gate import require_buzz_tool

        denied = require_buzz_tool(name)
        if denied:
            return denied
    fn = TOOL_IMPLS.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        return fn(**(arguments or {}))
    except TypeError as exc:
        return json.dumps({"error": f"Bad arguments for {name}: {exc}"})
