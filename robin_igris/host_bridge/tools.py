"""Carry host bridge tools — Manifest-mediated actions on the local device."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from aos.host_control import HostControlContract
from aos.kernel import AgentKernel


def _kernel() -> AgentKernel | None:
    root = os.getenv("ROBIN_USB_ROOT") or os.getenv("AOS_USB_ROOT")
    if not root:
        return None
    return AgentKernel.create(Path(root))


def _contract(k: AgentKernel | None = None) -> HostControlContract:
    k = k or _kernel()
    if k and k.host_control:
        return k.host_control
    # Dev fallback: disabled contract
    from aos.host_control import HostControlContract as HCC

    return HCC.from_manifest_raw({"host_control": {"enabled": False}})


def _ok(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _err(msg: str, **extra: Any) -> str:
    return json.dumps({"error": msg, **extra}, ensure_ascii=False)


def host_status() -> str:
    k = _kernel()
    c = _contract(k)
    out: dict[str, Any] = {"contract": c.status()}
    if k and getattr(k, "host_probe", None):
        out["probe"] = {
            "hostname": k.host_probe.get("hostname"),
            "os": k.host_probe.get("os"),
            "dirs": k.host_probe.get("dirs"),
        }
    return _ok(out)


def host_list_dir(path: str) -> str:
    c = _contract()
    ok, reason = c.allow_fs(path, "read")
    if not ok:
        return _err(reason)
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        return _err(f"not a directory: {p}")
    entries = []
    for child in sorted(p.iterdir())[:200]:
        entries.append(
            {
                "name": child.name,
                "type": "dir" if child.is_dir() else "file",
                "size": child.stat().st_size if child.is_file() else None,
            }
        )
    c._log("list_dir", {"path": str(p), "count": len(entries)})
    return _ok({"path": str(p), "entries": entries})


def host_read_file(path: str, max_bytes: int = 100_000) -> str:
    c = _contract()
    ok, reason = c.allow_fs(path, "read")
    if not ok:
        return _err(reason)
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return _err(f"not a file: {p}")
    size = p.stat().st_size
    if size > c.max_file_size_mb * 1024 * 1024:
        return _err(f"file exceeds max_file_size_mb={c.max_file_size_mb}")
    data = p.read_bytes()[: max(1, int(max_bytes))]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return _ok({"path": str(p), "encoding": "binary", "size": size, "preview_hex": data[:64].hex()})
    c._log("read_file", {"path": str(p), "bytes": len(data)})
    return _ok({"path": str(p), "size": size, "content": text})


def host_write_file(path: str, content: str, approval_token: str | None = None) -> str:
    c = _contract()
    p = Path(path).expanduser().resolve()
    if p.exists():
        ok, reason = c.allow_fs(path, "write")
        if not ok:
            return _err(reason)
        ap_ok, ap_reason = c.check_approval("overwrite", approval_token)
        if not ap_ok:
            token = c.request_approval("overwrite", {"path": str(p)})
            return _err(ap_reason, approval_token=token, queued=True)
    else:
        ok_c, reason_c = c.allow_fs(path, "create")
        ok_w, reason_w = c.allow_fs(path, "write")
        if not (ok_c or ok_w):
            return _err(reason_c if not ok_c else reason_w)
    if len(content.encode()) > c.max_file_size_mb * 1024 * 1024:
        return _err("content exceeds max_file_size_mb")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    c._log("write_file", {"path": str(p), "bytes": len(content.encode())})
    return _ok({"written": str(p), "bytes": len(content.encode())})


def host_delete_file(path: str, approval_token: str | None = None) -> str:
    c = _contract()
    ok, reason = c.allow_fs(path, "delete")
    if not ok:
        return _err(reason)
    # Either filesystem.require_approval_for=["delete"] or
    # computer_use.rules.confirm_before=["file_delete"] gates this.
    # Do not treat an ungated alias as approval for a gated one.
    for gate in ("delete", "file_delete"):
        if not c.needs_approval(gate):
            continue
        ap_ok, ap_reason = c.check_approval(gate, approval_token)
        if not ap_ok:
            token = c.request_approval("delete", {"path": str(path)})
            return _err(ap_reason, approval_token=token, queued=True)
    p = Path(path).expanduser().resolve()
    if p.is_file():
        p.unlink()
    elif p.is_dir():
        return _err("refusing to delete directories in v0 — files only")
    else:
        return _err(f"not found: {p}")
    c._log("delete_file", {"path": str(p)})
    return _ok({"deleted": str(p)})


def host_launch_app(app: str) -> str:
    c = _contract()
    ok, reason = c.allow_app(app, "launch")
    if not ok:
        return _err(reason)
    # Map friendly names to binaries
    mapping = {
        "code": ["code", "code-insiders"],
        "browser": ["xdg-open", "open", "firefox", "google-chrome", "chromium"],
        "terminal": ["gnome-terminal", "kitty", "alacritty", "x-terminal-emulator"],
        "finder": ["open", "xdg-open"],
        "explorer": ["explorer.exe", "xdg-open"],
    }
    candidates = mapping.get(app, [app])
    bin_path = None
    for name in candidates:
        bin_path = shutil.which(name)
        if bin_path:
            break
    if not bin_path:
        return _err(f"app binary not found for {app}", tried=candidates)
    if os.getenv("ROBIN_HOST_LIVE", "0") != "1":
        c._log("launch_app_dry", {"app": app, "bin": bin_path})
        return _ok({"launched": False, "dry_run": True, "app": app, "bin": bin_path})
    subprocess.Popen([bin_path], start_new_session=True)  # noqa: S603
    c._log("launch_app", {"app": app, "bin": bin_path})
    return _ok({"launched": True, "app": app, "bin": bin_path})


def host_computer_use(modality: str, gesture: str, detail: str = "") -> str:
    c = _contract()
    ok, reason = c.allow_computer_use(modality, gesture)
    if not ok:
        return _err(reason)
    live = bool(c.computer_use.get("live")) and os.getenv("ROBIN_HOST_LIVE", "0") == "1"
    c._log("computer_use", {"modality": modality, "gesture": gesture, "detail": detail, "live": live})
    if not live:
        return _ok(
            {
                "executed": False,
                "dry_run": True,
                "modality": modality,
                "gesture": gesture,
                "detail": detail,
                "hint": "Set computer_use.live=true and ROBIN_HOST_LIVE=1 for real input",
            }
        )
    return _err("live computer-use backend not bundled in v0 — dry_run only")


def host_run_command(command: str, cwd: str | None = None) -> str:
    c = _contract()
    ok, reason = c.allow_terminal(command, cwd=cwd)
    if not ok:
        return _err(reason)
    ap_ok, ap_reason = c.check_approval("sudo_commands" if "sudo" in command else "terminal", None)
    # terminal itself may not need approval; sudo already denied
    if os.getenv("ROBIN_HOST_LIVE", "0") != "1":
        c._log("run_command_dry", {"command": command, "cwd": cwd})
        return _ok({"executed": False, "dry_run": True, "command": command, "cwd": cwd})
    try:
        r = subprocess.run(
            command,
            shell=True,  # noqa: S602 — gated by Manifest deny patterns
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return _ok(
            {
                "executed": True,
                "returncode": r.returncode,
                "stdout": (r.stdout or "")[:8000],
                "stderr": (r.stderr or "")[:2000],
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


TOOL_IMPLS: dict[str, Callable[..., str]] = {
    "host_status": host_status,
    "host_list_dir": host_list_dir,
    "host_read_file": host_read_file,
    "host_write_file": host_write_file,
    "host_delete_file": host_delete_file,
    "host_launch_app": host_launch_app,
    "host_computer_use": host_computer_use,
    "host_run_command": host_run_command,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "host_status",
            "description": "Show Carry host-control contract and boot probe summary.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "host_list_dir",
            "description": "List a directory under Manifest-scoped host filesystem paths.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "host_read_file",
            "description": "Read a file under Manifest-scoped host paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_bytes": {"type": "integer", "default": 100000},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "host_write_file",
            "description": "Write/create a file under scoped paths. Overwrite may require approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "approval_token": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "host_delete_file",
            "description": "Delete a file under scoped paths (requires approval).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "approval_token": {"type": "string"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "host_launch_app",
            "description": "Launch an allowed host application (code, browser, terminal, …).",
            "parameters": {
                "type": "object",
                "properties": {"app": {"type": "string"}},
                "required": ["app"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "host_computer_use",
            "description": "Computer-use gesture (mouse/keyboard/clipboard/screenshot) if Manifest allows. Dry-run unless live.",
            "parameters": {
                "type": "object",
                "properties": {
                    "modality": {"type": "string", "description": "mouse|keyboard|clipboard|screenshot"},
                    "gesture": {"type": "string"},
                    "detail": {"type": "string"},
                },
                "required": ["modality", "gesture"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "host_run_command",
            "description": "Run a shell command if Manifest terminal.allowed (sudo denied). Dry-run unless ROBIN_HOST_LIVE=1.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "cwd": {"type": "string"},
                },
                "required": ["command"],
            },
        },
    },
]
