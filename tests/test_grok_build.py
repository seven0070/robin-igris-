"""Grok Build integration — coding sidecar for Robin."""

import json
from pathlib import Path
from unittest.mock import patch

from robin_igris.grok_build import GROK_BUILD_REPO, GROK_BUILD_SOURCE_REV, GrokBuildClient
from robin_igris.tools import TOOL_IMPLS, run_tool


def test_source_rev_pinned():
    assert len(GROK_BUILD_SOURCE_REV) == 40
    assert "xai-org/grok-build" in GROK_BUILD_REPO


def test_status_when_missing():
    c = GrokBuildClient(binary="/nonexistent/grok-binary-xyz")
    st = c.status()
    assert st["available"] is False
    assert "install" in st


def test_headless_missing_binary():
    c = GrokBuildClient(binary="/nonexistent/grok-binary-xyz")
    out = c.run_headless("hello")
    assert out["ok"] is False
    assert "not found" in out["error"].lower()


def test_headless_mock_success(tmp_path: Path):
    c = GrokBuildClient(binary="grok")

    class Fake:
        returncode = 0
        stdout = "done"
        stderr = ""

    with patch.object(c, "available", return_value=True):
        with patch("robin_igris.grok_build.client.subprocess.run", return_value=Fake()):
            out = c.run_headless("fix the bug", cwd=tmp_path)
    assert out["ok"] is True
    assert out["stdout"] == "done"


def test_tools_registered():
    assert "grok_status" in TOOL_IMPLS
    assert "grok_ask" in TOOL_IMPLS
    assert "grok_code" in TOOL_IMPLS


def test_grok_status_tool():
    out = json.loads(run_tool("grok_status", {}))
    assert out["name"] == "Grok Build"
    assert "repo" in out


def test_shell_grok_status(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    from aos.kernel import AgentKernel
    from aos.shell import AgentShell

    shell = AgentShell(AgentKernel.create(tmp_path))
    st = json.loads(shell.handle_line(":grok"))
    assert st["name"] == "Grok Build"
    assert "Grok Build" in shell.kernel.boot_context()
