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
            f"  usb root  : {self.kernel.root}",
            "",
            f"  capabilities allowed: {allowed}",
            f"  absent (no stubs)   : {denied}",
            "",
            "  Unplug USB or Ctrl+C = intentional shutdown (soul sealed).",
            "  Type a message, or :status / :soul / :goals / :quit",
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
        if text.startswith(":cap "):
            name = text[5:].strip()
            try:
                self.kernel.runtime.require(name)
                return f"capability {name!r}: allowed"
            except PermissionError as exc:
                return f"capability {name!r}: denied — {exc}"

        # Default: treat as agent utterance — record into soul.
        self.kernel.soul.append("episodic", f"user: {text}", meta={"role": "user"})
        tip = self.kernel.soul.tip().get("merkle_root", "")[:12]
        reply = (
            f"[AOS] Received on borrowed host. Soul tip advancing ({tip}…). "
            "Wire Hermes/companion for full reply (:status for capsule)."
        )
        self.kernel.soul.append("episodic", f"assistant: {reply}", meta={"role": "assistant"})
        return reply


def status_dict(kernel: AgentKernel) -> dict[str, Any]:
    return kernel.status()
