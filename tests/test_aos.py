"""Tests for Pendrive-Native Agent OS."""

from pathlib import Path

import pytest

from aos.kernel import AgentKernel
from aos.manifest import Manifest, ManifestRuntime
from aos.octopus import probe
from aos.soul import SoulStore


def test_manifest_gates_capabilities():
    m = Manifest.default()
    m.capabilities["network"] = True
    m.capabilities["shell_exec"] = False
    rt = ManifestRuntime(manifest=m)
    rt.synthesize({"has_network": False, "has_display": True, "has_audio_out": True, "has_audio_in": True})
    assert rt.effective["network"] is False  # hardware shrinks capsule
    assert rt.effective["display"] is True
    with pytest.raises(PermissionError):
        rt.require("shell_exec")


def test_soul_merkle_and_seal(tmp_path: Path):
    soul = SoulStore(tmp_path / "soul")
    soul.ensure_identity("Robin")
    soul.append("episodic", "Booted on borrowed host.")
    tip = soul.tip()
    assert tip["merkle_root"]
    assert soul.verify_seal()
    # New entry changes merkle root vs frozen tip until re-seal
    old = tip["merkle_root"]
    soul.append("semantic", "USB is home.")
    assert soul.merkle_root() != old
    soul._update_tip()
    assert soul.verify_seal()


def test_kernel_boot_and_mediate(tmp_path: Path):
    (tmp_path / ".robin_usb").touch()
    k = AgentKernel.create(tmp_path)
    assert k.soul.verify_seal()
    ctx = k.boot_context()
    assert "Manifest" in ctx or "capsule" in ctx
    assert "Borrowed host" in ctx or "Octopus" in ctx

    # filesystem_soul should be allowed
    out = k.mediate("filesystem_soul", "ping", lambda: "ok")
    assert out == "ok"

    with pytest.raises(PermissionError):
        k.mediate("shell_exec", "rm", lambda: None)

    tip = k.lifecycle.seal("test")
    assert tip["merkle_root"]


def test_octopus_probe_shape():
    info = probe()
    assert "has_display" in info
    assert "has_network" in info
    assert "platform" in info


def test_cli_init_and_status(tmp_path: Path):
    from aos.cli import main

    (tmp_path / ".robin_usb").touch()
    assert main(["init", "--root", str(tmp_path)]) == 0
    assert (tmp_path / "data" / "aos" / "manifest.json").exists()
    assert main(["status", "--root", str(tmp_path)]) == 0
    assert main(["boot-once", "--root", str(tmp_path), "--no-watch"]) == 0


def test_shell_commands(tmp_path: Path):
    from aos.shell import AgentShell

    (tmp_path / ".robin_usb").touch()
    k = AgentKernel.create(tmp_path)
    sh = AgentShell(k)
    assert "Pendrive Agent OS" in sh.banner()
    assert sh.handle_line(":quit") == "__QUIT__"
    assert "effective_capabilities" in sh.format_status()
    out = sh.handle_line("hello stick")
    assert "Soul tip" in out or "tip" in out.lower()
