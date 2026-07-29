"""Gate host_* tools behind Manifest host_control."""

from __future__ import annotations

import json
import os
from pathlib import Path


def require_host_tool(tool_name: str) -> str | None:
    root = os.getenv("ROBIN_USB_ROOT") or os.getenv("AOS_USB_ROOT")
    if not root:
        # Without USB root, still require explicit enable via env for safety
        if os.getenv("ROBIN_HOST_CONTROL", "0") != "1":
            return json.dumps(
                {
                    "error": "Host control disabled",
                    "hint": "Set ROBIN_USB_ROOT with host_control.enabled, or ROBIN_HOST_CONTROL=1 for dev",
                }
            )
        return None
    try:
        from aos.kernel import AgentKernel

        k = AgentKernel.create(Path(root))
        if not k.runtime.effective.get("host_control", False):
            return json.dumps(
                {
                    "error": "host_control capability absent",
                    "hint": "Set host_control.enabled=true in data/aos/manifest.json",
                }
            )
        if not k.runtime.allows_tool(tool_name):
            return json.dumps({"error": f"Tool {tool_name!r} denied by Manifest.tools"})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": f"host gate failed: {exc}"})
    return None
