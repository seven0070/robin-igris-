"""Carry host bridge — Manifest-scoped local device control."""

import json
from pathlib import Path

from aos.host_control import HostControlContract
from aos.host_probe import probe_host
from aos.kernel import AgentKernel
from robin_igris.tools import TOOL_IMPLS, run_tool


def test_host_tools_registered():
    assert "host_status" in TOOL_IMPLS
    assert "host_read_file" in TOOL_IMPLS
    assert "host_run_command" in TOOL_IMPLS


def test_host_disabled_by_default(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    k = AgentKernel.create(tmp_path)
    assert k.host_control is not None
    assert k.host_control.enabled is False
    out = json.loads(run_tool("host_list_dir", {"path": str(tmp_path)}))
    assert "error" in out


def test_scoped_fs_read_write(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    zone = tmp_path / "zone"
    zone.mkdir()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    from aos.manifest import Manifest

    man = Manifest.default()
    man.capabilities["host_control"] = True
    man.raw = {
        **man.raw,
        "host_control": {
            "enabled": True,
            "filesystem": {
                "paths": [{"path": str(zone), "access": ["read", "write", "create", "delete"]}],
                "rules": {"max_file_size_mb": 1, "require_approval_for": ["delete", "overwrite"]},
            },
            "applications": {"allowed": ["code"], "actions": ["launch"]},
            "computer_use": {"screenshot": True, "live": False, "mouse": ["click"], "keyboard": ["type"]},
            "terminal": {"allowed": False, "deny_patterns": ["sudo"]},
        },
        "tools": {**man.raw.get("tools", {}), **{f"host_{x}": True for x in (
            "status", "list_dir", "read_file", "write_file", "delete_file", "launch_app", "computer_use", "run_command"
        )}},
    }
    aos = tmp_path / "data" / "aos"
    aos.mkdir(parents=True)
    man.save(aos / "manifest.json")

    # write new file
    target = zone / "hello.txt"
    out = json.loads(run_tool("host_write_file", {"path": str(target), "content": "hi"}))
    assert out.get("written") or "error" not in out
    assert target.read_text() == "hi"

    # read
    out = json.loads(run_tool("host_read_file", {"path": str(target)}))
    assert out.get("content") == "hi"

    # outside path denied
    out = json.loads(run_tool("host_read_file", {"path": str(tmp_path / "secret.txt")}))
    assert "error" in out

    # delete needs approval
    out = json.loads(run_tool("host_delete_file", {"path": str(target)}))
    assert out.get("queued") or "approval" in out.get("error", "").lower()
    assert target.exists()

    # approve and delete
    monkeypatch.setenv("ROBIN_HOST_APPROVE", "1")
    out = json.loads(run_tool("host_delete_file", {"path": str(target)}))
    assert out.get("deleted")
    assert not target.exists()


def test_sudo_structurally_denied():
    c = HostControlContract.from_manifest_raw(
        {
            "host_control": {
                "enabled": True,
                "terminal": {"allowed": True, "deny_patterns": ["sudo"], "cwd_must_be_under": []},
                "filesystem": {"paths": [], "rules": {}},
                "applications": {"allowed": [], "actions": []},
                "computer_use": {},
            }
        }
    )
    ok, reason = c.allow_terminal("sudo apt install evil")
    assert ok is False
    assert "sudo" in reason.lower() or "denied" in reason.lower()


def test_host_probe_shape():
    r = probe_host()
    assert r["probe"].startswith("carry-host")
    assert "os" in r
    assert "commands" in r
