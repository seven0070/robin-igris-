"""Host Control Probe — one-shot at boot (Octopus-inspired).

Builds a structured capability map of the borrowed device for agent context.
Discovery is read-only; acting requires HostControlContract.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
from pathlib import Path
from typing import Any

from aos.octopus import probe as octopus_probe


def _which_many(names: list[str]) -> dict[str, str | None]:
    return {n: shutil.which(n) for n in names}


def probe_host() -> dict[str, Any]:
    """One-shot host capability report."""
    hw = octopus_probe()
    home = Path.home()
    report: dict[str, Any] = {
        "probe": "carry-host-control/v1",
        "hostname": socket.gethostname(),
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "hardware": hw,
        "home": str(home),
        "dirs": {
            "documents": str((home / "Documents").resolve()) if (home / "Documents").exists() else None,
            "desktop": str((home / "Desktop").resolve()) if (home / "Desktop").exists() else None,
            "downloads": str((home / "Downloads").resolve()) if (home / "Downloads").exists() else None,
        },
        "commands": _which_many(
            [
                "code",
                "code-insiders",
                "xdg-open",
                "open",
                "explorer.exe",
                "gnome-terminal",
                "kitty",
                "alacritty",
                "firefox",
                "google-chrome",
                "chromium",
                "nmcli",
            ]
        ),
        "env": {
            "DISPLAY": os.getenv("DISPLAY"),
            "WAYLAND_DISPLAY": os.getenv("WAYLAND_DISPLAY"),
            "SHELL": os.getenv("SHELL"),
            "USER": os.getenv("USER") or os.getenv("USERNAME"),
        },
    }
    return report


def as_prompt(report: dict[str, Any] | None = None) -> str:
    report = report or probe_host()
    return (
        "## Host Control Probe (borrowed device)\n"
        "Structured capability map at boot — do not discover by trial and error.\n"
        "Acting on the host still requires Manifest host_control grants.\n"
        f"```json\n{json.dumps(report, indent=2, default=str)}\n```\n"
    )
