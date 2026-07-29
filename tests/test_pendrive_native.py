"""Robin — pendrive-native mind (hardware-up)."""

import json
from pathlib import Path

from aos.kernel import AgentKernel
from robin_igris.pendrive_native import Robin
from robin_igris.tools import TOOL_IMPLS, run_tool


def test_blank_says_unknown(tmp_path: Path):
    m = Robin.create(tmp_path)
    out = m.ask("What is the capital of France?")
    assert out["found"] is False
    assert "don't know" in out["reply"].lower()
    assert out["architecture"] == "robin-v0"
    assert out["name"] == "Robin"


def test_teach_then_find(tmp_path: Path):
    m = Robin.create(tmp_path)
    teach = m.ask("Paris is the capital of France.")
    assert teach["found"] is True
    ask = m.ask("What is the capital of France?")
    assert ask["found"] is True
    assert "paris" in ask["reply"].lower()


def test_born_named_robin(tmp_path: Path):
    m = Robin.create(tmp_path)
    assert m.store.get_meta("name") == "Robin"
    st = m.status()
    assert st["name"] == "Robin"


def test_name_identity(tmp_path: Path):
    m = Robin.create(tmp_path)
    out = m.ask("Your name is Iris.")
    assert "iris" in out["reply"].lower()
    assert m.store.counts()["propositions"] >= 1


def test_idle_and_overnight_metabolism(tmp_path: Path):
    m = Robin.create(tmp_path)
    m.ask("Berlin is the capital of Germany.")
    m.ask("Paris is the capital of France.")
    idle = m.idle()
    assert idle["phase"] == "idle"
    assert idle["power_mw"] == 10.0
    night = m.consolidate()
    assert night["phase"] == "overnight"
    assert night["synthesized"] >= 1
    assert m.store.get_meta("soul_rewrite") is not None


def test_fts_open_query(tmp_path: Path):
    m = Robin.create(tmp_path)
    m.ask("Carry is the pendrive agent OS.")
    out = m.ask("Tell me about Carry pendrive")
    assert out["found"] is True


def test_kernel_wires_robin(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    k = AgentKernel.create(tmp_path)
    assert k.pendrive_native is not None
    assert "Robin" in k.boot_context()


def test_shell_robin(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    from aos.shell import AgentShell

    shell = AgentShell(AgentKernel.create(tmp_path))
    st = json.loads(shell.handle_line(":robin"))
    assert st["architecture"] == "robin-v0"
    assert st["name"] == "Robin"
    teach = json.loads(shell.handle_line(":robin Madrid is the capital of Spain."))
    assert teach["found"] is True
    ask = json.loads(shell.handle_line(":pne What is the capital of Spain?"))
    assert "madrid" in ask["reply"].lower()


def test_robin_tools(tmp_path: Path, monkeypatch):
    assert "robin_ask" in TOOL_IMPLS
    assert "pne_ask" in TOOL_IMPLS
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    out = json.loads(run_tool("robin_ask", {"text": "What is the capital of Atlantis?"}))
    assert out["name"] == "Robin"
    assert out["found"] is False
