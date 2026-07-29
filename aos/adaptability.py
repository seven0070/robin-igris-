"""Carry Micro Hardware — native RAM + adaptability for a self-contained pendrive.

On real Carry PCB silicon: LPDDR is private, PMIC negotiates USB PD, thermal
sensors throttle the SoC, DP Alt Mode drives Airi, secure enclave owns identity.

In today's userspace bridge: the same contract is simulated from Manifest + env
(+ /sys when available) so the agent already adapts its behavior.
"""

from __future__ import annotations

import json
import os
import platform
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# BOM / form-factor targets for Carry Micro v0 (design reference, not a claim of stock HW)
BOARD_PROFILES: dict[str, dict[str, Any]] = {
    "carry-micro-v0-sim": {
        "form_factor_mm": [60, 25, 10],
        "soc": "simulated (host CPU)",
        "native_ram_mb": 4096,
        "storage_gb": 128,
        "wifi": "optional",
        "cost_prototype_usd": [80, 120],
        "cost_volume_usd": [35, 50],
        "retail_target_usd": [60, 80],
        "real_silicon": False,
    },
    "carry-micro-rk3588s": {
        "form_factor_mm": [60, 25, 10],
        "soc": "Rockchip RK3588S",
        "native_ram_mb": 8192,
        "storage_gb": 128,
        "wifi": "AP6275P WiFi6+BT5.3",
        "npu": True,
        "dp_alt_mode": True,
        "enclave": "OP-TEE / SoC secure world",
        "real_silicon": True,
    },
    "carry-micro-jh7110": {
        "form_factor_mm": [60, 25, 10],
        "soc": "StarFive JH7110 (RISC-V)",
        "native_ram_mb": 4096,
        "storage_gb": 64,
        "wifi": "optional module",
        "npu": False,
        "dp_alt_mode": True,
        "enclave": "optional",
        "real_silicon": True,
    },
}

DEFAULT_ADAPTABILITY = {
    "board": "carry-micro-v0-sim",
    "native_ram": {
        "enabled": True,
        "capacity_mb": 4096,
        "private": True,
        "note": "Agent memory envelope — not borrowed host RAM on real PCB",
    },
    "power": {
        "profile": "auto",
        "respect_host_battery": True,
        "budgets_w": {"usb2": 2.5, "usb3": 4.5, "pd": 15.0, "battery_pack": 5.0},
    },
    "thermal": {
        "mode": "balanced",
        "throttle_c": 80.0,
        "modes": ["silent", "balanced", "performance"],
    },
    "display": {
        "prefer": "auto",
        "paths": ["dp_alt", "usb_gadget", "wifi_ui", "headless"],
    },
    "enclave": {
        "required": False,
        "tamper_wipe": True,
        "attestation": "software-stub",
    },
    "scheduler": {
        "prioritize_voice_when_interactive": True,
        "batch_when_idle": True,
    },
}

POWER_PROFILES = {
    "powersave": {
        "label": "USB 2.0 / constrained",
        "max_w": 2.5,
        "llm_speed": 0.4,
        "avatar": "minimal",
        "heavy_compute": False,
    },
    "standard": {
        "label": "USB 3.0",
        "max_w": 4.5,
        "llm_speed": 1.0,
        "avatar": "full",
        "heavy_compute": True,
    },
    "turbo": {
        "label": "USB-C PD",
        "max_w": 15.0,
        "llm_speed": 1.25,
        "avatar": "full",
        "heavy_compute": True,
    },
}


def _read_thermal_c() -> float | None:
    override = os.getenv("CARRY_THERMAL_C")
    if override:
        try:
            return float(override)
        except ValueError:
            pass
    best: float | None = None
    try:
        for zone in sorted(Path("/sys/class/thermal").glob("thermal_zone*/temp")):
            raw = zone.read_text().strip()
            if not raw.isdigit():
                continue
            c = int(raw) / 1000.0
            best = c if best is None else max(best, c)
    except Exception:
        pass
    return best


def _host_on_battery() -> bool | None:
    override = os.getenv("CARRY_HOST_BATTERY")
    if override is not None:
        return override.lower() in {"1", "true", "yes"}
    try:
        base = Path("/sys/class/power_supply")
        if not base.exists():
            return None
        for supply in base.iterdir():
            t = (supply / "type").read_text().strip() if (supply / "type").exists() else ""
            if t != "Battery":
                continue
            status = (supply / "status").read_text().strip() if (supply / "status").exists() else ""
            if status in {"Discharging", "Not charging"}:
                return True
            if status == "Charging":
                return False
    except Exception:
        pass
    return None


def _detect_power_source(prefer: str = "auto") -> str:
    env = os.getenv("CARRY_POWER_SOURCE", "").lower()
    if env in {"usb2", "usb3", "pd", "battery", "battery_pack"}:
        return env
    if prefer != "auto":
        return prefer
    # Userspace heuristics — real PCB reads PMIC / USB PD CC negotiation
    if os.getenv("CARRY_PD", "").lower() in {"1", "true", "yes"}:
        return "pd"
    # Linux often exposes USB device speed poorly from userspace; default standard
    return "usb3"


def _power_profile_for_source(source: str) -> str:
    return {
        "usb2": "powersave",
        "usb3": "standard",
        "pd": "turbo",
        "battery": "powersave",
        "battery_pack": "standard",
    }.get(source, "standard")


def _detect_display_path(prefer: str = "auto") -> str:
    env = os.getenv("CARRY_DISPLAY_PATH", "").lower()
    if env in {"dp_alt", "usb_gadget", "wifi_ui", "headless"}:
        return env
    if prefer != "auto":
        return prefer
    if os.getenv("CARRY_DP_ALT", "").lower() in {"1", "true", "yes"}:
        return "dp_alt"
    if os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY") or platform.system() == "Windows":
        # Borrowed host display (userspace) or DP Alt when on silicon
        return "dp_alt" if os.getenv("CARRY_BOARD", "").startswith("carry-micro-rk") else "usb_gadget"
    if os.getenv("CARRY_WIFI_UI", "").lower() in {"1", "true", "yes"}:
        return "wifi_ui"
    return "headless"


def _enclave_status(cfg: dict[str, Any]) -> dict[str, Any]:
    """Software stub for physical secure enclave + tamper response."""
    present = os.getenv("CARRY_ENCLAVE", "").lower() in {"1", "true", "yes"}
    tampered = os.getenv("CARRY_TAMPER", "").lower() in {"1", "true", "yes"}
    required = bool(cfg.get("required", False))
    wipe = bool(cfg.get("tamper_wipe", True))
    alive = present and not (tampered and wipe)
    return {
        "present": present,
        "required": required,
        "tampered": tampered,
        "identity_alive": alive if present else (not required),
        "attestation": cfg.get("attestation", "software-stub"),
        "note": (
            "On real Carry PCB: keys born in enclave, die on casing open. "
            "Userspace stub — set CARRY_ENCLAVE=1 to simulate."
        ),
    }


@dataclass
class AdaptabilityState:
    """Resolved adaptation snapshot fed to the agent at boot and on refresh."""

    board: str
    board_profile: dict[str, Any]
    native_ram: dict[str, Any]
    power: dict[str, Any]
    thermal: dict[str, Any]
    display: dict[str, Any]
    enclave: dict[str, Any]
    host_awareness: dict[str, Any]
    behavior: dict[str, Any]
    scheduler: dict[str, Any]
    probed_at: float = field(default_factory=time.time)

    def as_dict(self) -> dict[str, Any]:
        return {
            "board": self.board,
            "board_profile": self.board_profile,
            "native_ram": self.native_ram,
            "power": self.power,
            "thermal": self.thermal,
            "display": self.display,
            "enclave": self.enclave,
            "host_awareness": self.host_awareness,
            "behavior": self.behavior,
            "scheduler": self.scheduler,
            "probed_at": self.probed_at,
        }

    def context_prompt(self) -> str:
        return (
            "## Carry Micro Hardware (adaptability)\n"
            "You have (or simulate) private native RAM and must adapt to power, thermal,\n"
            "display path, and host context. Prefer voice latency when interactive;\n"
            "batch memory/skill work when idle. Never assume unlimited host power.\n"
            f"```json\n{json.dumps(self.as_dict(), indent=2, default=str)}\n```\n"
        )


@dataclass
class AdaptabilityContract:
    """Manifest-backed adaptability + probe."""

    raw: dict[str, Any]
    state: AdaptabilityState | None = None

    @classmethod
    def from_manifest_raw(cls, raw: dict[str, Any]) -> "AdaptabilityContract":
        block = dict(DEFAULT_ADAPTABILITY)
        user = raw.get("adaptability") or raw.get("micro_hw") or {}
        # shallow-merge top keys; nested dicts overwritten by user section
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(block.get(k), dict):
                merged = dict(block[k])
                merged.update(v)
                block[k] = merged
            else:
                block[k] = v
        board = os.getenv("CARRY_BOARD") or str(block.get("board") or "carry-micro-v0-sim")
        block["board"] = board
        return cls(raw=block)

    def probe(self, *, host_hardware: dict[str, Any] | None = None) -> AdaptabilityState:
        cfg = self.raw
        board = str(cfg.get("board") or "carry-micro-v0-sim")
        profile = dict(BOARD_PROFILES.get(board) or BOARD_PROFILES["carry-micro-v0-sim"])
        profile["id"] = board

        ram_cfg = cfg.get("native_ram") or {}
        capacity = int(os.getenv("CARRY_NATIVE_RAM_MB") or ram_cfg.get("capacity_mb") or profile.get("native_ram_mb") or 4096)
        real = bool(profile.get("real_silicon"))
        native_ram = {
            "enabled": bool(ram_cfg.get("enabled", True)),
            "capacity_mb": capacity,
            "private": bool(ram_cfg.get("private", True)),
            "backed_by": "on-board LPDDR" if real else "simulated envelope (userspace)",
            "host_ram_bytes": (host_hardware or {}).get("ram_bytes"),
            "note": ram_cfg.get("note")
            or "Private agent working set — cloning eMMC does not clone enclave identity.",
        }

        power_cfg = cfg.get("power") or {}
        pref = str(power_cfg.get("profile") or "auto")
        # prefer may be auto|usb2|usb3|pd|battery|powersave|standard|turbo
        if pref in POWER_PROFILES:
            source_label = {
                "powersave": "usb2",
                "standard": "usb3",
                "turbo": "pd",
            }.get(pref, "usb3")
            pname = pref
        else:
            source_label = _detect_power_source(pref if pref != "auto" else "auto")
            pname = _power_profile_for_source(source_label)
        host_batt = _host_on_battery()
        if power_cfg.get("respect_host_battery", True) and host_batt is True and pname == "turbo":
            pname = "standard"
        pdetail = dict(POWER_PROFILES[pname])
        budgets = power_cfg.get("budgets_w") or DEFAULT_ADAPTABILITY["power"]["budgets_w"]
        power = {
            "source": source_label,
            "profile": pname,
            **pdetail,
            "budget_w": budgets.get(source_label, pdetail["max_w"]),
            "host_on_battery": host_batt,
        }

        th_cfg = cfg.get("thermal") or {}
        temp = _read_thermal_c()
        mode = os.getenv("CARRY_THERMAL_MODE") or str(th_cfg.get("mode") or "balanced")
        if mode not in {"silent", "balanced", "performance"}:
            mode = "balanced"
        throttle_c = float(th_cfg.get("throttle_c") or 80.0)
        throttled = bool(temp is not None and temp >= throttle_c)
        if throttled and mode == "performance":
            mode = "balanced"
        thermal = {
            "temp_c": temp,
            "mode": mode,
            "throttle_c": throttle_c,
            "throttled": throttled,
            "perf_scale": 0.5 if throttled else {"silent": 0.7, "balanced": 1.0, "performance": 1.15}[mode],
        }

        disp_cfg = cfg.get("display") or {}
        path = _detect_display_path(str(disp_cfg.get("prefer") or "auto"))
        display = {
            "path": path,
            "airi_direct": path == "dp_alt",
            "avatar_quality": (
                "full"
                if path == "dp_alt" and power["avatar"] == "full"
                else "simple"
                if path in {"usb_gadget", "wifi_ui"}
                else "none"
            ),
        }

        enclave = _enclave_status(cfg.get("enclave") or {})

        host_awareness = {
            "host_on_battery": host_batt,
            "host_has_network": (host_hardware or {}).get("has_network"),
            "host_has_display": (host_hardware or {}).get("has_display"),
            "polite_if_locked": True,
            "note": "Do not drain host laptop battery for heavy jobs; wait if screensaver/locked.",
        }

        # Behavior adaptation the agent should follow
        behavior = {
            "voice": "quieter" if host_batt else "normal",
            "avatar": display["avatar_quality"] if not throttled else "simple",
            "llm_speed": round(power["llm_speed"] * thermal["perf_scale"], 2),
            "allow_heavy_compute": bool(power["heavy_compute"]) and not throttled and not (host_batt and power["profile"] == "powersave"),
            "patient_mode": bool(host_batt) or throttled or power["profile"] == "powersave",
        }

        sched_cfg = cfg.get("scheduler") or {}
        scheduler = {
            "prioritize_voice_when_interactive": bool(sched_cfg.get("prioritize_voice_when_interactive", True)),
            "batch_when_idle": bool(sched_cfg.get("batch_when_idle", True)),
            "hint": (
                "interactive → low-latency voice path; "
                "idle → memory consolidation + Kairn compile; "
                "throttled → defer heavy inference"
            ),
            "defer_heavy": throttled or power["profile"] == "powersave",
        }

        self.state = AdaptabilityState(
            board=board,
            board_profile=profile,
            native_ram=native_ram,
            power=power,
            thermal=thermal,
            display=display,
            enclave=enclave,
            host_awareness=host_awareness,
            behavior=behavior,
            scheduler=scheduler,
        )
        return self.state

    def refresh(self, *, host_hardware: dict[str, Any] | None = None) -> AdaptabilityState:
        return self.probe(host_hardware=host_hardware)

    def status(self) -> dict[str, Any]:
        if self.state is None:
            self.probe()
        assert self.state is not None
        return self.state.as_dict()

    def context_prompt(self) -> str:
        if self.state is None:
            self.probe()
        assert self.state is not None
        return self.state.context_prompt()

    def allows_heavy_compute(self) -> bool:
        if self.state is None:
            self.probe()
        assert self.state is not None
        return bool(self.state.behavior.get("allow_heavy_compute"))
