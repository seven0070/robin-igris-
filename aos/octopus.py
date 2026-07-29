"""Octopus-inspired one-shot hardware discovery → Infrastructure-as-Prompts."""

from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any


def _which(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(cmd: list[str], timeout: float = 2.0) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "") + (r.stderr or "")
    except Exception:
        return ""


def probe() -> dict[str, Any]:
    """Discover borrowed host peripherals for this boot."""
    info: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "processor": platform.processor() or platform.machine(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count() or 1,
    }

    # Memory
    mem_total = None
    try:
        if Path("/proc/meminfo").exists():
            for line in Path("/proc/meminfo").read_text().splitlines():
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1]) * 1024
                    break
    except Exception:
        pass
    info["ram_bytes"] = mem_total

    # Display / audio heuristics
    info["has_display"] = bool(
        os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY") or platform.system() == "Windows"
    )
    info["has_audio_out"] = platform.system() in {"Windows", "Darwin", "Linux"}
    info["has_audio_in"] = info["has_audio_out"]  # assume mic if audio stack exists
    info["has_camera"] = bool(
        Path("/dev/video0").exists() if platform.system() == "Linux" else False
    )

    # Network
    info["has_network"] = False
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=1.5).close()
        info["has_network"] = True
    except Exception:
        try:
            socket.gethostbyname("example.com")
            info["has_network"] = True
        except Exception:
            info["has_network"] = False

    # GPU
    info["has_gpu"] = False
    info["gpu_notes"] = ""
    if _which("nvidia-smi"):
        out = _run(["nvidia-smi", "-L"])
        info["has_gpu"] = "GPU" in out or "NVIDIA" in out
        info["gpu_notes"] = out.strip()[:400]
    elif platform.system() == "Darwin":
        info["has_gpu"] = True
        info["gpu_notes"] = "Apple/Metal likely available"
    elif platform.system() == "Windows":
        info["has_gpu"] = True  # optimistic; refine later
        info["gpu_notes"] = "Windows host — GPU status unknown"

    # USB root awareness
    info["usb_root"] = os.getenv("ROBIN_USB_ROOT")
    info["aos_mode"] = os.getenv("ROBIN_AOS_MODE", "userspace")

    return info


def as_prompt(info: dict[str, Any] | None = None) -> str:
    info = info or probe()
    return (
        "## Borrowed host (Octopus probe)\n"
        "You are booting on interchangeable hardware. Treat peripherals as loaned.\n"
        f"```json\n{json.dumps(info, indent=2, default=str)}\n```\n"
    )
