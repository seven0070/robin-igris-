"""Executive Monitor — Sophia System 3 orchestration over Hermes."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from robin_igris.system3.budget import Metabolism
from robin_igris.system3.heartbeat import Heartbeat, IntrinsicDrive
from robin_igris.system3.journal import GrowthJournal


@dataclass
class ExecutiveMonitor:
    """Meta-cognitive loop: context → Hermes → appraisal → journal / budget."""

    agent_name: str = field(
        default_factory=lambda: os.getenv("AGENT_NAME", "Robin Igris")
    )
    data_root: Path = field(default_factory=lambda: Path("data/system3"))
    wake_cost_usd: float = 0.02
    journal: GrowthJournal = field(init=False)
    metabolism: Metabolism = field(init=False)
    heartbeat: Heartbeat = field(init=False)

    def __post_init__(self) -> None:
        self.data_root = Path(self.data_root)
        self.journal = GrowthJournal(self.data_root)
        self.journal.ensure_defaults(self.agent_name)
        self.metabolism = Metabolism(path=self.data_root / "metabolism.json")
        self.heartbeat = Heartbeat()

    def build_system_context(self) -> str:
        status = self.metabolism.status()
        return (
            f"You are {self.agent_name}, a persistent companion (System 3 + Hermes).\n"
            f"Metabolism: balance=${status['balance_usd']:.4f} alive={status['alive']}.\n"
            "If the wake is not worth the budget, reply with exactly: WAIT\n\n"
            + self.journal.context_block()
        )

    def wake(
        self,
        user_text: str,
        *,
        kind: str = "user",
        drive: IntrinsicDrive | None = None,
        chat_fn: Any | None = None,
    ) -> str:
        """Run one cognitive cycle through Hermes (or fallback chat_fn)."""
        if not self.metabolism.alive:
            return "⚠ Metabolism exhausted — agent is operationally dead until budget is credited."

        if not self.metabolism.debit(self.wake_cost_usd, reason=f"wake:{kind}"):
            return "⚠ Insufficient budget for this wake."

        messages = [
            {"role": "system", "content": self.build_system_context()},
            {"role": "user", "content": user_text},
        ]

        reply = self._chat(messages, chat_fn)
        appraisal = self._appraise(kind, user_text, reply, drive)

        if reply.strip().upper().startswith("WAIT"):
            # Partial refund for declining low-value work
            self.metabolism.credit(self.wake_cost_usd * 0.5, reason="wait-refund")
            self.journal.append_episode(
                kind="wait",
                summary="Declined low-value wake.",
                appraisal=appraisal,
                goal=user_text[:160],
            )
            return reply

        self.journal.append_episode(
            kind=kind if drive is None else f"intrinsic:{drive.value}",
            summary=reply[:800],
            appraisal=appraisal,
            goal=user_text[:200],
        )
        return reply

    def heartbeat_once(self, chat_fn: Any | None = None) -> str:
        drive, prompt = self.heartbeat.compose_prompt()
        self.heartbeat.mark()
        return self.wake(prompt, kind="heartbeat", drive=drive, chat_fn=chat_fn)

    def _chat(self, messages: list[dict], chat_fn: Any | None) -> str:
        if chat_fn is not None:
            return chat_fn(messages)
        try:
            from robin_igris.hermes_client import chat as hermes_chat

            return hermes_chat(messages, session_key="robin-igris-system3")
        except Exception as exc:  # noqa: BLE001
            # Fallback: local lightweight agent if Hermes is down
            try:
                from robin_igris.agent import Agent

                agent = Agent(name=self.agent_name)
                # Flatten to a single user turn with system preamble
                sys_txt = messages[0]["content"]
                user_txt = messages[-1]["content"]
                agent.history[0]["content"] = sys_txt
                return agent.chat(user_txt)
            except Exception as exc2:  # noqa: BLE001
                return f"Error contacting brain: hermes={exc}; fallback={exc2}"

    def _appraise(
        self,
        kind: str,
        goal: str,
        reply: str,
        drive: IntrinsicDrive | None,
    ) -> str:
        """Verbal policy appraisal (OpenLife VPO / Sophia hybrid reward) — local heuristic."""
        bits = [f"kind={kind}"]
        if drive:
            bits.append(f"drive={drive.value}")
        if reply.strip().upper().startswith("WAIT"):
            bits.append("intrinsic=budget_conserved")
        elif len(reply) > 40:
            bits.append("extrinsic=produced_output")
            bits.append("coherence=ok")
        else:
            bits.append("extrinsic=thin_output")
        return "; ".join(bits)

    def status(self) -> dict:
        return {
            "agent": self.agent_name,
            "metabolism": self.metabolism.status(),
            "heartbeat_interval_s": self.heartbeat.interval_s,
            "episodes": len(list((self.data_root / "episodes").glob("*.json"))),
        }
