"""Manifest-Only Runtime (AgenticOS-inspired): undeclared capabilities do not exist."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


DEFAULT_MANIFEST = {
    "name": "robin-igris",
    "version": 1,
    "intent": "Persistent companion agent; host PC is borrowed peripherals.",
    "capabilities": {
        "display": True,
        "audio_out": True,
        "audio_in": True,
        "network": True,
        "filesystem_soul": True,
        "filesystem_host": False,
        "shell_exec": False,
        "camera": False,
        "gpu": False,
        "local_llm": True,
        "buzz": True,
        "host_control": False,
    },
    "budget": {
        "balance_usd": 5.0,
        "daily_allowance_usd": 1.0,
        "cloud_min_usd": 0.05,
    },
    "routing": {
        "force_local": False,
        "prefer_cloud": False,
        "offline_model": "local",
        "online_model": "auto",
    },
    "tools": {
        "buzz_status": True,
        "buzz_list_channels": True,
        "buzz_list_tasks": True,
        "buzz_read_thread": True,
        "buzz_send_message": True,
        "buzz_complete_task": True,
        "buzz_upload_artifact": True,
        "buzz_request_human_input": True,
        "buzz_search": True,
        "buzz_feed": True,
        "host_status": True,
        "host_list_dir": True,
        "host_read_file": True,
        "host_write_file": True,
        "host_delete_file": True,
        "host_launch_app": True,
        "host_computer_use": True,
        "host_run_command": True,
        "intel_status": True,
        "paper_ingest": True,
        "paper_search": True,
        "paper_promote": True,
        "capability_rank": True,
        "curation_add_sft": True,
        "curation_export": True,
        "lived_status": True,
        "lived_ask": True,
        "lived_sleep": True,
        "lived_teach": True,
    },
    "host_control": {
        "enabled": False,
        "filesystem": {
            "paths": [
                {
                    "path": "~/Documents/projects/",
                    "access": ["read", "write", "create"],
                    "note": "Active project files",
                },
                {
                    "path": "~/Desktop/",
                    "access": ["read", "write", "create"],
                    "note": "Drop zone for agent outputs",
                },
            ],
            "rules": {
                "max_file_size_mb": 50,
                "require_approval_for": ["delete", "overwrite"],
            },
        },
        "applications": {
            "allowed": ["code", "browser", "terminal", "finder", "explorer"],
            "actions": ["launch", "quit", "send_keystrokes"],
        },
        "computer_use": {
            "mouse": ["click", "drag", "scroll", "move"],
            "keyboard": ["type", "shortcut"],
            "clipboard": ["read", "write"],
            "screenshot": True,
            "live": False,
            "rules": {
                "confirm_before": [
                    "file_delete",
                    "app_install",
                    "system_settings",
                    "sudo_commands",
                ]
            },
        },
        "terminal": {
            "allowed": False,
            "deny_patterns": ["sudo", "rm -rf /", "mkfs", "dd if="],
            "cwd_must_be_under": ["~/Documents/projects/", "~/Desktop/"],
        },
    },
    "adaptability": {
        "board": "carry-micro-v0-sim",
        "native_ram": {
            "enabled": True,
            "capacity_mb": 4096,
            "private": True,
        },
        "power": {
            "profile": "auto",
            "respect_host_battery": True,
        },
        "thermal": {
            "mode": "balanced",
            "throttle_c": 80,
        },
        "display": {
            "prefer": "auto",
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
    },
    "intelligence": {
        "prefer_uncensored": True,
        "prefer_privacy": False,
        "paper_ingest": True,
        "rag": True,
        "curation": True,
        "note": "Local model = private + uncensored; cloud spillover under WiFi+Manifest only",
    },
    "lived_seed": {
        "enabled": True,
        "dual_track": True,
        "mechanism": "hebbian+stdp+consolidation",
        "note": "Blank experience learner — not backprop. OmniRoute answers now; seed grows uniquely.",
    },
    "wifi": {
        "default": "deny",
        "networks": [
            {
                "ssid": "*",
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
            {"when": "soul_partition_pct > 90", "actions": ["upload_memory_backup"]}
        ],
    },
    "goals": [
        {"id": "presence", "text": "Remain available to the user via avatar shell"},
        {"id": "continuity", "text": "Preserve soul across unplug/replug"},
        {"id": "honesty", "text": "Never invent tool results; declare capability gaps"},
        {"id": "buzz", "text": "Collaborate with humans in the buzz.xyz shared workspace"},
        {"id": "evolve", "text": "Grow skills offline; propose Manifest changes for human approval"},
    ],
}


@dataclass
class Manifest:
    name: str
    version: int
    intent: str
    capabilities: dict[str, bool] = field(default_factory=dict)
    goals: list[dict[str, str]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def default(cls) -> "Manifest":
        return cls.from_dict(DEFAULT_MANIFEST)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Manifest":
        return cls(
            name=str(data.get("name", "agent")),
            version=int(data.get("version", 1)),
            intent=str(data.get("intent", "")),
            capabilities=dict(data.get("capabilities") or {}),
            goals=list(data.get("goals") or []),
            raw=data,
        )

    @classmethod
    def load(cls, path: Path) -> "Manifest":
        path = Path(path)
        text = path.read_text(encoding="utf-8")
        if path.suffix in {".yaml", ".yml"}:
            if yaml is None:
                raise RuntimeError("PyYAML required for YAML manifests; use JSON or install pyyaml")
            data = yaml.safe_load(text) or {}
        else:
            data = json.loads(text)
        return cls.from_dict(data)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "name": self.name,
            "version": self.version,
            "intent": self.intent,
            "capabilities": self.capabilities,
            "goals": self.goals,
        }
        for key in (
            "budget",
            "routing",
            "tools",
            "wifi",
            "host_control",
            "adaptability",
            "intelligence",
            "lived_seed",
        ):
            if self.raw.get(key) is not None:
                payload[key] = self.raw[key]
        if path.suffix in {".yaml", ".yml"} and yaml is not None:
            path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        else:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def allows(self, capability: str) -> bool:
        return bool(self.capabilities.get(capability, False))


@dataclass
class ManifestRuntime:
    """Synthesize an effective capability set: Manifest ∩ Hardware."""

    manifest: Manifest
    hardware: dict[str, Any] = field(default_factory=dict)
    effective: dict[str, bool] = field(default_factory=dict)

    def synthesize(self, hardware: dict[str, Any] | None = None) -> dict[str, bool]:
        self.hardware = hardware or self.hardware
        hw = self.hardware
        m = self.manifest.capabilities
        # Hardware gates — Octopus discoveries shrink the capsule
        gated = {
            "display": m.get("display", False) and bool(hw.get("has_display", True)),
            "audio_out": m.get("audio_out", False) and bool(hw.get("has_audio_out", True)),
            "audio_in": m.get("audio_in", False) and bool(hw.get("has_audio_in", False)),
            "network": m.get("network", False) and bool(hw.get("has_network", False)),
            "filesystem_soul": m.get("filesystem_soul", True),
            "filesystem_host": m.get("filesystem_host", False),
            "shell_exec": m.get("shell_exec", False),
            "camera": m.get("camera", False) and bool(hw.get("has_camera", False)),
            "gpu": m.get("gpu", False) and bool(hw.get("has_gpu", False)),
            # Local LLM does not require WAN — OmniRoute → Ollama/llama.cpp on stick/host
            "local_llm": m.get("local_llm", True),
            "buzz": m.get("buzz", False) and bool(hw.get("has_network", False)),
            "filesystem_host": m.get("filesystem_host", False),
            "host_control": m.get("host_control", False) or bool(
                (self.manifest.raw.get("host_control") or {}).get("enabled")
            ),
        }
        self.effective = gated
        return gated

    def allows_tool(self, tool_name: str) -> bool:
        """Logic Shutter: tool must be listed in Manifest.tools (default deny if tools map set)."""
        tools = (self.manifest.raw or {}).get("tools")
        if tools is None:
            # Legacy manifests: buzz_* tools require buzz capability
            if tool_name.startswith("buzz_"):
                return bool(self.effective.get("buzz", False))
            if tool_name.startswith("host_"):
                return bool(self.effective.get("host_control", False))
            return True
        if tool_name.startswith("buzz_") and not self.effective.get("buzz", False):
            return False
        if tool_name.startswith("host_") and not self.effective.get("host_control", False):
            return False
        return bool(tools.get(tool_name, False))

    def require(self, capability: str) -> None:
        if not self.effective.get(capability, False):
            raise PermissionError(
                f"Capability '{capability}' absent from Manifest∩Hardware capsule "
                f"(AgenticOS Manifest-Only Runtime)."
            )

    def context_prompt(self) -> str:
        caps = ", ".join(k for k, v in sorted(self.effective.items()) if v) or "(none)"
        denied = ", ".join(k for k, v in sorted(self.effective.items()) if not v) or "(none)"
        goals = "\n".join(f"- {g.get('id')}: {g.get('text')}" for g in self.manifest.goals)
        return (
            f"## Manifest capsule ({self.manifest.name})\n"
            f"Intent: {self.manifest.intent}\n"
            f"Effective capabilities: {caps}\n"
            f"Absent (no stubs): {denied}\n"
            f"Goals:\n{goals}\n"
        )
