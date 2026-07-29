"""Core agent loop for Robin Igris."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from robin_igris import llm
from robin_igris.tools import TOOL_SCHEMAS, run_tool

SYSTEM_PROMPT = """You are {name}, a capable AI agent.

Personality: sharp, concise, and helpful. Prefer direct answers over fluff.
You have tools — use them when they improve accuracy (math, live info, time, notes).
After using tools, synthesize a clear final answer for the user.
If a tool fails, say so briefly and continue with what you know.
"""


@dataclass
class Agent:
    name: str = field(default_factory=lambda: os.getenv("AGENT_NAME", "Robin Igris"))
    max_tool_rounds: int = 6
    history: list[dict[str, Any]] = field(default_factory=list)
    on_tool: Callable[[str, dict[str, Any], str], None] | None = None

    def __post_init__(self) -> None:
        if not self.history:
            self.history = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(name=self.name),
                }
            ]

    def reset(self) -> None:
        self.history = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(name=self.name),
            }
        ]

    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})

        for _ in range(self.max_tool_rounds):
            message = llm.chat(self.history, tools=TOOL_SCHEMAS)
            tool_calls = getattr(message, "tool_calls", None) or []

            # Persist assistant turn (with optional tool_calls)
            assistant_entry: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
            }
            if tool_calls:
                assistant_entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                    for tc in tool_calls
                ]
            self.history.append(assistant_entry)

            if not tool_calls:
                return (message.content or "").strip() or "(empty response)"

            for tc in tool_calls:
                name = tc.function.name
                raw_args = tc.function.arguments or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}
                result = run_tool(name, args)
                if self.on_tool:
                    self.on_tool(name, args, result)
                self.history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )

        # Cap reached — one last completion without tools
        message = llm.chat(self.history, tools=None)
        text = (message.content or "").strip() or (
            "I hit the tool-call limit. Please rephrase or ask a narrower question."
        )
        self.history.append({"role": "assistant", "content": text})
        return text
