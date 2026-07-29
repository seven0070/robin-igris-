"""Semantic Boundary Gateway — Manifest gates for Buzz tools."""

from __future__ import annotations

import json
import os
from pathlib import Path


def require_buzz_tool(tool_name: str) -> str | None:
    """Return error JSON if tool is not allowed; else None."""
    root = os.getenv("ROBIN_USB_ROOT") or os.getenv("AOS_USB_ROOT")
    if not root:
        # No AOS root — allow if BUZZ_PRIVATE_KEY present (dev mode)
        if not os.getenv("BUZZ_PRIVATE_KEY"):
            return json.dumps(
                {
                    "error": "Buzz not configured",
                    "hint": "Set BUZZ_PRIVATE_KEY and BUZZ_RELAY_URL (see docs/BUZZ.md)",
                }
            )
        return None

    try:
        from aos.kernel import AgentKernel

        k = AgentKernel.create(Path(root))
        if not k.runtime.effective.get("buzz", False):
            return json.dumps(
                {
                    "error": "Capability 'buzz' absent from Manifest∩Hardware",
                    "hint": "Enable network + buzz in data/aos/manifest.json, or go online",
                }
            )
        if not k.runtime.allows_tool(tool_name):
            return json.dumps(
                {
                    "error": f"Tool '{tool_name}' denied by Manifest.tools Logic Shutter",
                }
            )
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": f"Buzz gate failed: {exc}"})
    return None
