"""Agent-is-the-shell: no desktop — avatar/CLI is the UI."""

from __future__ import annotations

import json
from typing import Any

from aos.kernel import AgentKernel


class AgentShell:
    """Thin presentation layer over the Agent Kernel.

    There is no window manager, no file browser, no login screen.
    The shell:
      1. Shows boot / capability status
      2. Relays user text → soul + (optionally) Hermes
      3. Surfaces soul tip / goals as OS state
    """

    def __init__(self, kernel: AgentKernel) -> None:
        self.kernel = kernel

    def banner(self) -> str:
        st = self.kernel.status()
        tip = st.get("soul_tip") or {}
        root = tip.get("merkle_root", "")[:16] if isinstance(tip, dict) else str(tip)[:16]
        hw = st.get("hardware") or {}
        caps = st.get("effective_capabilities") or {}
        allowed = ", ".join(k for k, v in sorted(caps.items()) if v) or "(none)"
        denied = ", ".join(k for k, v in sorted(caps.items()) if not v) or "(none)"
        lines = [
            "╔══════════════════════════════════════════════╗",
            "║         Pendrive Agent OS — session          ║",
            "╚══════════════════════════════════════════════╝",
            f"  manifest  : {st.get('manifest')}",
            f"  soul tip  : {root}…",
            f"  sealed ok : {st.get('soul_sealed_ok')}",
            f"  host      : {hw.get('hostname')} ({hw.get('system')})",
            f"  display   : {hw.get('has_display')}  network: {hw.get('has_network')}",
            "  axioms   : offline-first · permissioned WiFi · self-evolving shell",
            f"  wifi     : {(st.get('wifi') or {}).get('current_ssid')} "
            f"(pending queue={st.get('offline_queue_pending', 0)})",
            f"  usb root : {self.kernel.root}",
            "",
            f"  capabilities allowed: {allowed}",
            f"  absent (no stubs)   : {denied}",
            "",
            "  Unplug USB or Ctrl+C = intentional shutdown (soul sealed).",
            "  :status :soul :goals :buzz :wifi :evolve :flush :quit",
            "",
        ]
        return "\n".join(lines)

    def format_status(self) -> str:
        return json.dumps(self.kernel.status(), indent=2, default=str)

    def format_soul(self) -> str:
        tip = self.kernel.soul.tip()
        return json.dumps(
            {
                "tip": tip,
                "sealed_ok": self.kernel.soul.verify_seal(),
                "counts": {
                    k: len(self.kernel.soul.list_class(k, limit=10_000))  # type: ignore[arg-type]
                    for k in ("episodic", "semantic", "procedural", "working", "identity")
                },
            },
            indent=2,
            default=str,
        )

    def format_goals(self) -> str:
        return json.dumps(
            [
                {"id": g.id, "text": g.text, "progress": g.progress, "status": g.status}
                for g in self.kernel.goals
            ],
            indent=2,
        )

    def handle_line(self, line: str) -> str:
        text = line.strip()
        if not text:
            return ""
        if text in {":quit", ":exit", ":q"}:
            return "__QUIT__"
        if text == ":status":
            return self.format_status()
        if text == ":soul":
            return self.format_soul()
        if text == ":goals":
            return self.format_goals()
        if text == ":buzz":
            try:
                from robin_igris.buzz.tools import buzz_status

                return buzz_status()
            except Exception as exc:  # noqa: BLE001
                return json.dumps({"error": str(exc)})
        if text == ":wifi":
            if not self.kernel.wifi:
                return json.dumps({"error": "no wifi contract"})
            return json.dumps(self.kernel.wifi.status(), indent=2)
        if text == ":evolve":
            if not self.kernel.evolution:
                return json.dumps({"error": "no evolution store"})
            return json.dumps(self.kernel.evolution.status(), indent=2)
        if text.startswith(":checkpoint"):
            if not self.kernel.evolution:
                return json.dumps({"error": "no evolution store"})
            label = text[len(":checkpoint") :].strip() or "manual"
            return json.dumps(self.kernel.evolution.checkpoint(label), indent=2)
        if text.startswith(":rollback"):
            if not self.kernel.evolution:
                return json.dumps({"error": "no evolution store"})
            cid = text[len(":rollback") :].strip() or None
            return json.dumps(self.kernel.evolution.rollback(cid), indent=2, default=str)
        if text == ":flush":
            def _send(p: dict) -> Any:
                from robin_igris.buzz.tools import buzz_send_message

                return json.loads(
                    buzz_send_message(
                        p.get("content", ""),
                        channel=p.get("channel"),
                        reply_to=p.get("reply_to"),
                    )
                )

            handlers = {
                "buzz_send_message": _send,
                "check_buzz": lambda p: {"ok": True, "payload": p},
            }
            return json.dumps(self.kernel.flush_queue(handlers), indent=2, default=str)
        if text.startswith(":cap "):
            name = text[5:].strip()
            try:
                self.kernel.runtime.require(name)
                return f"capability {name!r}: allowed"
            except PermissionError as exc:
                return f"capability {name!r}: denied — {exc}"

        # Default: OmniRoute with offline-first routing (local when no WAN).
        self.kernel.soul.append("episodic", f"user: {text}", meta={"role": "user"})
        caps = self.kernel.runtime.effective
        if not (caps.get("local_llm") or caps.get("network")):
            tip = self.kernel.soul.tip().get("merkle_root", "")[:12]
            reply = f"[AOS] No LLM capability in capsule. tip={tip}…"
            self.kernel.soul.append("episodic", f"assistant: {reply}", meta={"role": "assistant"})
            return reply

        try:
            from robin_igris.omniroute import chat_text
            from robin_igris.routing import from_capsule, routing_context

            budget = None
            raw_budget = (self.kernel.manifest.raw or {}).get("budget") or {}
            if "balance_usd" in raw_budget:
                budget = float(raw_budget["balance_usd"])
            decision = from_capsule(
                caps,
                user_text=text,
                budget_usd=budget,
                manifest_raw=self.kernel.manifest.raw,
            )
            ctx = self.kernel.boot_context() + "\n" + routing_context(decision)
            reply = chat_text(
                [
                    {"role": "system", "content": ctx},
                    {"role": "user", "content": text},
                ],
                route=decision,
            ).strip() or "(empty OmniRoute reply)"
            self.kernel.audit(
                "llm_route",
                {"mode": decision.mode, "model": decision.model, "reason": decision.reason},
            )
        except Exception as exc:  # noqa: BLE001
            tip = self.kernel.soul.tip().get("merkle_root", "")[:12]
            reply = (
                f"[AOS] OmniRoute unreachable ({exc}). Soul tip={tip}…. "
                "Start OmniRoute on :20128; for offline, register a local provider."
            )
        self.kernel.soul.append("episodic", f"assistant: {reply}", meta={"role": "assistant"})
        return reply


def status_dict(kernel: AgentKernel) -> dict[str, Any]:
    return kernel.status()
