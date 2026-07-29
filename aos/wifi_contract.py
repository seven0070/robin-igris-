"""Permissioned WiFi contract — offline default; online is requested.

Axiom 2: the agent connects only to SSIDs you authorize, and only for actions
declared in the Manifest. Networking is a userspace gateway, not a free syscall.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_WIFI = {
    "default": "deny",
    "networks": [
        {
            "ssid": "*",  # wildcard for userspace bridge until real SSID probe
            "actions": [
                "sync_memory",
                "check_buzz",
                "pull_models",
                "omniroute_cloud",
                "web_search",
            ],
            "budget_mb_month": 500,
        }
    ],
    "emergency": [
        {
            "when": "soul_partition_pct > 90",
            "actions": ["upload_memory_backup"],
        }
    ],
}


@dataclass
class WifiNetwork:
    ssid: str
    actions: set[str]
    budget_mb_month: float = 500.0


@dataclass
class WifiContract:
    """Logic Shutter for network actions."""

    networks: list[WifiNetwork] = field(default_factory=list)
    default_deny: bool = True
    emergency: list[dict[str, Any]] = field(default_factory=list)
    usage_path: Path | None = None
    _usage: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_manifest_raw(cls, raw: dict[str, Any], usage_path: Path | None = None) -> "WifiContract":
        wifi = raw.get("wifi") or DEFAULT_WIFI
        nets: list[WifiNetwork] = []
        for n in wifi.get("networks") or []:
            nets.append(
                WifiNetwork(
                    ssid=str(n.get("ssid", "*")),
                    actions=set(n.get("actions") or []),
                    budget_mb_month=float(n.get("budget_mb_month", 500)),
                )
            )
        return cls(
            networks=nets,
            default_deny=str(wifi.get("default", "deny")).lower() != "allow",
            emergency=list(wifi.get("emergency") or []),
            usage_path=usage_path,
        )._load()

    def _load(self) -> "WifiContract":
        if self.usage_path and self.usage_path.exists():
            try:
                self._usage = json.loads(self.usage_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._usage = {}
        return self

    def _save(self) -> None:
        if not self.usage_path:
            return
        self.usage_path.parent.mkdir(parents=True, exist_ok=True)
        self.usage_path.write_text(json.dumps(self._usage, indent=2), encoding="utf-8")

    def _month_key(self, ssid: str) -> str:
        return f"{ssid}:{time.strftime('%Y-%m')}"

    def current_ssid(self) -> str | None:
        """Best-effort SSID probe (Linux nmcli / env override)."""
        env = os.getenv("ROBIN_WIFI_SSID") or os.getenv("BUZZ_ALLOWED_SSID")
        if env:
            return env
        try:
            import subprocess

            r = subprocess.run(
                ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if r.returncode == 0:
                for line in (r.stdout or "").splitlines():
                    # active:ssid  →  yes:MyNetwork
                    if line.startswith("yes:"):
                        return line.split(":", 1)[1] or None
        except Exception:  # noqa: BLE001
            pass
        # Userspace bridge on host OS: treat connected internet as wildcard match
        if os.getenv("ROBIN_WIFI_ASSUME_STAR", "1") == "1":
            return "*"
        return None

    def _match(self, ssid: str | None) -> WifiNetwork | None:
        if not ssid:
            return None
        for n in self.networks:
            if n.ssid == ssid or n.ssid == "*":
                return n
        return None

    def allow(self, action: str, *, ssid: str | None = None, bytes_estimate: int = 0) -> tuple[bool, str]:
        """Return (allowed, reason). Offline / unknown SSID → deny unless emergency."""
        ssid = ssid or self.current_ssid()
        if not ssid:
            return False, "offline: no authorized WiFi associated (default deny)"

        net = self._match(ssid)
        if net is None:
            if self.default_deny:
                return False, f"ssid {ssid!r} not in Manifest wifi.networks"
            return True, "default allow"

        if action not in net.actions:
            return False, f"action {action!r} not permitted on ssid {ssid!r}"

        used = float(self._usage.get(self._month_key(net.ssid), 0.0))
        add_mb = bytes_estimate / (1024 * 1024)
        if used + add_mb > net.budget_mb_month:
            return False, f"wifi budget exhausted for {net.ssid} ({used:.1f}/{net.budget_mb_month} MB)"

        return True, f"ok ssid={ssid} action={action}"

    def record_usage(self, *, ssid: str | None = None, bytes_used: int = 0) -> None:
        ssid = ssid or self.current_ssid() or "*"
        key = self._month_key(ssid)
        self._usage[key] = float(self._usage.get(key, 0.0)) + bytes_used / (1024 * 1024)
        self._save()

    def require(self, action: str, **kwargs: Any) -> None:
        ok, reason = self.allow(action, **kwargs)
        if not ok:
            raise PermissionError(f"WiFi contract denied: {reason}")

    def status(self) -> dict[str, Any]:
        ssid = self.current_ssid()
        return {
            "current_ssid": ssid,
            "default": "deny" if self.default_deny else "allow",
            "networks": [
                {
                    "ssid": n.ssid,
                    "actions": sorted(n.actions),
                    "budget_mb_month": n.budget_mb_month,
                    "used_mb_month": self._usage.get(self._month_key(n.ssid), 0.0),
                }
                for n in self.networks
            ],
            "emergency": self.emergency,
        }
