"""Tiny network probe shared by System 3 routing (avoid importing full aos.octopus)."""

from __future__ import annotations

import os
import socket


def has_network(timeout: float = 1.5) -> bool:
    if os.getenv("ROBIN_FORCE_OFFLINE", "").lower() in {"1", "true", "yes"}:
        return False
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=timeout).close()
        return True
    except Exception:  # noqa: BLE001
        try:
            socket.gethostbyname("example.com")
            return True
        except Exception:  # noqa: BLE001
            return False
