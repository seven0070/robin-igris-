"""Executive Monitor — Sophia System 3 orchestration over Hermes."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from robin_igris.system3.budget import Metabolism
from robin_igris.system3.cadvp import Channel, DeliveryBus
from robin_igris.system3.heartbeat import Heartbeat, IntrinsicDrive
from robin_igris.system3.journal import GrowthJournal


@dataclass
class ExecutiveMonitor:
    """Meta-cognitive loop: context → Hermes → appraisal → journal / CADVP delivery."""

    agent_name: str = field(
        default_factory=lambda: os.getenv("AGENT_NAME", "Robin Igris")
    )
    data_root: Path = field(
        default_factory=lambda: Path(
            os.getenv("ROBIN_SYSTEM3_ROOT", "data/system3")
        )
    )
    wake_cost_usd: float = 0.02
    journal: GrowthJournal = field(init=False)
    metabolism: Metabolism = field(init=False)
    heartbeat: Heartbeat = field(init=False)
    bus: DeliveryBus = field(init=False)

    def __post_init__(self) -> None:
        self.data_root = Path(self.data_root)
        self.journal = GrowthJournal(self.data_root)
        self.journal.ensure_defaults(self.agent_name)
        self.metabolism = Metabolism(path=self.data_root / "metabolism.json")
        self.heartbeat = Heartbeat()
        self.bus = DeliveryBus(self.data_root / "delivery")

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

        ep_kind = kind if drive is None else f"intrinsic:{drive.value}"
        self.journal.append_episode(
            kind=ep_kind,
            summary=reply[:800],
            appraisal=appraisal,
            goal=user_text[:200],
        )

        # Heartbeat / scheduled wakes must NOT use Hermes cron memory (Channel C
        # fracture: skip_memory=True). Persist via CADVP Channel A + inverse verify.
        if kind in {"heartbeat", "cron", "scheduled"} or drive is not None:
            receipt = self.bus.deliver(
                target=self.agent_name.replace(" ", "-").lower(),
                kind=ep_kind,
                content=reply[:2000],
                meta={
                    "goal": user_text[:200],
                    "appraisal": appraisal,
                    "drive": drive.value if drive else None,
                },
                preferred_channel=Channel.DIRECT_STORE,
            )
            if not receipt.confirmed:
                appraisal = f"{appraisal}; cadvp=FAILED:{receipt.cc0.reason}"
                self.journal.append_episode(
                    kind="cadvp_failure",
                    summary=f"Delivery not confirmed via {receipt.channel.value}",
                    appraisal=appraisal,
                    goal=user_text[:160],
                    meta=receipt.to_dict(),
                )
                return (
                    f"{reply}\n\n⚠ CADVP delivery failed "
                    f"({receipt.channel.value}): {receipt.cc0.reason}"
                )

        return reply

    def heartbeat_once(self, chat_fn: Any | None = None) -> str:
        drive, prompt = self.heartbeat.compose_prompt()
        self.heartbeat.mark()
        return self.wake(prompt, kind="heartbeat", drive=drive, chat_fn=chat_fn)

    def _chat(self, messages: list[dict], chat_fn: Any | None) -> str:
        if chat_fn is not None:
            return chat_fn(messages)
        # Primary LLM: OmniRoute (https://github.com/diegosouzapw/OmniRoute)
        try:
            from robin_igris.omniroute import chat_text

            return chat_text(messages)
        except Exception as exc:  # noqa: BLE001
            try:
                from robin_igris.hermes_client import chat as hermes_chat

                return hermes_chat(messages, session_key="robin-igris-system3")
            except Exception as exc_h:  # noqa: BLE001
                try:
                    from robin_igris.agent import Agent

                    agent = Agent(name=self.agent_name)
                    sys_txt = messages[0]["content"]
                    user_txt = messages[-1]["content"]
                    agent.history[0]["content"] = sys_txt
                    return agent.chat(user_txt)
                except Exception as exc2:  # noqa: BLE001
                    return (
                        f"Error contacting brain: omniroute={exc}; "
                        f"hermes={exc_h}; fallback={exc2}"
                    )

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
        cc0 = self.bus.probe(Channel.CRON_DELEGATED)
        safe = self.bus.probe(Channel.DIRECT_STORE)
        return {
            "agent": self.agent_name,
            "metabolism": self.metabolism.status(),
            "heartbeat_interval_s": self.heartbeat.interval_s,
            "episodes": len(list((self.data_root / "episodes").glob("*.json"))),
            "cadvp": {
                "channel_A": {"available": safe.available, "reason": safe.reason},
                "channel_C_cron": {
                    "available": cc0.available,
                    "reason": cc0.reason,
                    "fractured": not cc0.cc0_pass,
                },
                "inbox": len(self.bus.list_inbox()),
            },
        }
