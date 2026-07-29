"""Carry Host Bridge — Manifest-scoped control of the borrowed host device.

You trust the pendrive and the host; the agent is the mediator.
The Manifest is the contract: undeclared host actions are structurally impossible.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_HOST_CONTROL = {
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
}


def _expand(path: str) -> Path:
    return Path(path).expanduser().resolve()


@dataclass
class PathGrant:
    path: Path
    access: set[str]
    note: str = ""


@dataclass
class HostControlContract:
    enabled: bool
    grants: list[PathGrant]
    max_file_size_mb: float
    require_approval_for: set[str]
    apps_allowed: set[str]
    app_actions: set[str]
    computer_use: dict[str, Any]
    terminal_allowed: bool
    terminal_deny: list[str]
    terminal_cwd_roots: list[Path]
    approval_dir: Path | None = None
    audit: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_manifest_raw(
        cls,
        raw: dict[str, Any],
        *,
        approval_dir: Path | None = None,
    ) -> "HostControlContract":
        hc = raw.get("host_control") or DEFAULT_HOST_CONTROL
        grants: list[PathGrant] = []
        for p in (hc.get("filesystem") or {}).get("paths") or []:
            access = set(p.get("access") or [])
            grants.append(
                PathGrant(
                    path=_expand(str(p.get("path", ""))),
                    access=access,
                    note=str(p.get("note") or ""),
                )
            )
        rules = (hc.get("filesystem") or {}).get("rules") or {}
        apps = hc.get("applications") or {}
        term = hc.get("terminal") or {}
        cwd_roots = [_expand(x) for x in (term.get("cwd_must_be_under") or [])]
        return cls(
            enabled=bool(hc.get("enabled", False)),
            grants=grants,
            max_file_size_mb=float(rules.get("max_file_size_mb", 50)),
            require_approval_for=set(rules.get("require_approval_for") or []),
            apps_allowed=set(apps.get("allowed") or []),
            app_actions=set(apps.get("actions") or []),
            computer_use=dict(hc.get("computer_use") or {}),
            terminal_allowed=bool(term.get("allowed", False)),
            terminal_deny=list(term.get("deny_patterns") or []),
            terminal_cwd_roots=cwd_roots,
            approval_dir=approval_dir,
        )

    def _log(self, kind: str, detail: dict[str, Any]) -> None:
        self.audit.append({"ts": time.time(), "kind": kind, **detail})

    def grant_for(self, path: Path) -> PathGrant | None:
        path = path.expanduser().resolve()
        for g in self.grants:
            try:
                path.relative_to(g.path)
                return g
            except ValueError:
                if path == g.path:
                    return g
        return None

    def allow_fs(self, path: str | Path, action: str) -> tuple[bool, str]:
        if not self.enabled:
            return False, "host_control.enabled is false"
        # capability filesystem_host also required at Manifest∩Hardware layer
        p = _expand(str(path))
        grant = self.grant_for(p)
        if grant is None:
            return False, f"path {p} outside Manifest host_control.filesystem.paths"
        if action not in grant.access:
            return False, f"action {action!r} not in grant for {grant.path} ({sorted(grant.access)})"
        return True, f"ok {action} under {grant.path}"

    def needs_approval(self, action: str) -> bool:
        return action in self.require_approval_for or action in set(
            (self.computer_use.get("rules") or {}).get("confirm_before") or []
        )

    def check_approval(self, action: str, token: str | None = None) -> tuple[bool, str]:
        if not self.needs_approval(action):
            return True, "no approval required"
        if os.getenv("ROBIN_HOST_APPROVE", "").lower() in {"1", "true", "yes"}:
            return True, "approved via ROBIN_HOST_APPROVE"
        if token and self.approval_dir:
            f = self.approval_dir / f"{token}.approved"
            if f.exists():
                return True, f"approved token {token}"
        return False, f"approval required for {action} (Airi confirm / ROBIN_HOST_APPROVE=1 / token file)"

    def request_approval(self, action: str, detail: dict[str, Any]) -> str:
        """Write pending approval; return token id."""
        import uuid

        token = str(uuid.uuid4())[:8]
        if self.approval_dir:
            self.approval_dir.mkdir(parents=True, exist_ok=True)
            pending = {
                "token": token,
                "action": action,
                "detail": detail,
                "ts": time.time(),
                "prompt": f"Approve host action {action}? Place {token}.approved to allow.",
            }
            (self.approval_dir / f"{token}.pending.json").write_text(
                json.dumps(pending, indent=2), encoding="utf-8"
            )
        self._log("approval_requested", {"token": token, "action": action, "detail": detail})
        return token

    def allow_app(self, app: str, action: str) -> tuple[bool, str]:
        if not self.enabled:
            return False, "host_control.enabled is false"
        if app not in self.apps_allowed:
            return False, f"app {app!r} not in Manifest applications.allowed"
        if action not in self.app_actions:
            return False, f"app action {action!r} not permitted"
        return True, "ok"

    def allow_computer_use(self, modality: str, gesture: str) -> tuple[bool, str]:
        if not self.enabled:
            return False, "host_control.enabled is false"
        cu = self.computer_use
        allowed = set(cu.get(modality) or [])
        if modality == "screenshot":
            return (True, "ok") if cu.get("screenshot") else (False, "screenshot denied")
        if gesture not in allowed:
            return False, f"{modality}.{gesture} not in Manifest computer_use"
        return True, "ok"

    def allow_terminal(self, command: str, cwd: str | None = None) -> tuple[bool, str]:
        if not self.enabled or not self.terminal_allowed:
            return False, "terminal not allowed in Manifest"
        low = command.lower()
        for pat in self.terminal_deny:
            if pat.lower() in low:
                return False, f"denied pattern {pat!r}"
        if "sudo" in low.split():
            return False, "sudo structurally denied (not in Manifest)"
        if cwd and self.terminal_cwd_roots:
            c = _expand(cwd)
            if not any(self._under(c, r) for r in self.terminal_cwd_roots):
                return False, f"cwd {c} outside terminal.cwd_must_be_under"
        return True, "ok"

    @staticmethod
    def _under(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return path == root

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "paths": [
                {"path": str(g.path), "access": sorted(g.access), "note": g.note} for g in self.grants
            ],
            "apps": sorted(self.apps_allowed),
            "terminal_allowed": self.terminal_allowed,
            "computer_use": {
                "screenshot": bool(self.computer_use.get("screenshot")),
                "live": bool(self.computer_use.get("live")),
            },
            "require_approval_for": sorted(self.require_approval_for),
            "recent_audit": self.audit[-10:],
        }

    def context_prompt(self) -> str:
        st = self.status()
        return (
            "## Host control (Carry bridge)\n"
            "You may act on the borrowed host only within Manifest host_control.\n"
            "Undeclared paths/apps/commands are structurally denied.\n"
            f"```json\n{json.dumps(st, indent=2)}\n```\n"
        )
