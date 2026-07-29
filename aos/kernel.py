"""Agent Kernel — goal-progress control plane (AOS-inspired)."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from aos.lifecycle import Lifecycle
from aos.manifest import Manifest, ManifestRuntime
from aos.octopus import as_prompt as octopus_prompt
from aos.octopus import probe as octopus_probe
from aos.soul import SoulStore


@dataclass
class Goal:
    id: str
    text: str
    progress: float = 0.0
    status: str = "open"  # open | active | done | blocked
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentKernel:
    root: Path
    manifest: Manifest
    soul: SoulStore
    runtime: ManifestRuntime
    lifecycle: Lifecycle
    goals: list[Goal] = field(default_factory=list)
    audit_path: Path = field(init=False)
    hardware: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, usb_root: Path, manifest_path: Path | None = None) -> "AgentKernel":
        usb_root = Path(usb_root)
        aos_data = usb_root / "data" / "aos"
        aos_data.mkdir(parents=True, exist_ok=True)
        soul = SoulStore(aos_data / "soul")
        soul.ensure_identity("Robin Igris")

        if manifest_path and Path(manifest_path).exists():
            manifest = Manifest.load(Path(manifest_path))
        else:
            default_path = aos_data / "manifest.json"
            if default_path.exists():
                manifest = Manifest.load(default_path)
            else:
                manifest = Manifest.default()
                manifest.save(default_path)

        hardware = octopus_probe()
        runtime = ManifestRuntime(manifest=manifest)
        runtime.synthesize(hardware)
        life = Lifecycle(soul=soul, log_path=aos_data / "lifecycle.jsonl")
        kernel = cls(
            root=usb_root,
            manifest=manifest,
            soul=soul,
            runtime=runtime,
            lifecycle=life,
            hardware=hardware,
        )
        kernel.audit_path = aos_data / "audit.jsonl"
        kernel.goals = [
            Goal(id=g.get("id", str(uuid.uuid4())), text=g.get("text", ""))
            for g in manifest.goals
        ]
        kernel.audit("boot", {"hardware": hardware, "effective": runtime.effective})
        return kernel

    def audit(self, kind: str, payload: dict[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps({"ts": time.time(), "kind": kind, "payload": payload}, default=str)
                + "\n"
            )

    def mediate(self, capability: str, action: str, fn: Callable[[], Any]) -> Any:
        """Deterministic tool mediation — AOS boundary."""
        self.runtime.require(capability)
        self.audit("mediate", {"capability": capability, "action": action})
        try:
            result = fn()
            self.audit("mediate_ok", {"capability": capability, "action": action})
            return result
        except Exception as exc:
            self.audit("mediate_fail", {"capability": capability, "action": action, "error": str(exc)})
            raise

    def schedule_next(self) -> Goal | None:
        """Pick next open goal by lowest progress (simple goal-progress scheduler)."""
        open_goals = [g for g in self.goals if g.status in {"open", "active"}]
        if not open_goals:
            return None
        open_goals.sort(key=lambda g: g.progress)
        g = open_goals[0]
        g.status = "active"
        return g

    def report_progress(self, goal_id: str, progress: float, note: str = "") -> None:
        for g in self.goals:
            if g.id == goal_id:
                g.progress = max(0.0, min(1.0, progress))
                if g.progress >= 1.0:
                    g.status = "done"
                self.audit("goal_progress", {"id": goal_id, "progress": g.progress, "note": note})
                if note:
                    self.soul.append("episodic", f"Goal {goal_id}: {note}", meta={"goal": goal_id})
                return

    def boot_context(self) -> str:
        return (
            "# Pendrive-Native Agent OS\n"
            "You are the operating system shell. There is no desktop. The avatar is the UI.\n"
            "Unplugging the USB is intentional shutdown — preserve the soul.\n\n"
            + self.runtime.context_prompt()
            + "\n"
            + octopus_prompt(self.hardware)
            + "\n"
            + self.soul.context_prompt()
        )

    def status(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.name,
            "effective_capabilities": self.runtime.effective,
            "goals": [
                {"id": g.id, "text": g.text, "progress": g.progress, "status": g.status}
                for g in self.goals
            ],
            "soul_tip": self.soul.tip(),
            "soul_sealed_ok": self.soul.verify_seal(),
            "hardware": {
                k: self.hardware.get(k)
                for k in (
                    "hostname",
                    "system",
                    "has_display",
                    "has_network",
                    "has_gpu",
                    "usb_root",
                )
            },
        }
