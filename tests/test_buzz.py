"""Buzz.xyz integration — Manifest gate + client unit tests (no live relay)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aos.manifest import Manifest, ManifestRuntime
from robin_igris.buzz.client import BuzzClient, BuzzConfig, BuzzError
from robin_igris.buzz.tools import buzz_status
from robin_igris.tools import TOOL_IMPLS, run_tool


def test_buzz_tools_registered():
    assert "buzz_send_message" in TOOL_IMPLS
    assert "buzz_list_tasks" in TOOL_IMPLS
    assert "buzz_request_human_input" in TOOL_IMPLS


def test_manifest_buzz_requires_network():
    m = Manifest.default()
    m.capabilities["buzz"] = True
    m.raw = {**m.raw, "tools": {"buzz_send_message": True}}
    rt = ManifestRuntime(manifest=m)
    rt.synthesize({"has_network": False, "has_display": True})
    assert rt.effective["buzz"] is False
    assert rt.allows_tool("buzz_send_message") is False

    rt.synthesize({"has_network": True, "has_display": True})
    assert rt.effective["buzz"] is True
    assert rt.allows_tool("buzz_send_message") is True
    assert rt.allows_tool("buzz_unknown") is False


def test_buzz_status_no_cli():
    out = json.loads(buzz_status())
    assert "cli_available" in out
    assert out["workspace"] == "https://buzz.xyz"


def test_gate_without_key(monkeypatch):
    monkeypatch.delenv("ROBIN_USB_ROOT", raising=False)
    monkeypatch.delenv("AOS_USB_ROOT", raising=False)
    monkeypatch.delenv("BUZZ_PRIVATE_KEY", raising=False)
    denied = json.loads(run_tool("buzz_list_channels", {}))
    assert "error" in denied


def test_client_run_mocked():
    cfg = BuzzConfig(
        relay_url="https://example.communities.buzz.xyz",
        private_key="nsec1test",
        cli_bin="buzz",
        default_channel="chan-1",
    )
    client = BuzzClient(cfg)
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = json.dumps([{"name": "general"}])
    fake.stderr = ""
    with patch("robin_igris.buzz.client.subprocess.run", return_value=fake) as run:
        data = client.list_channels()
        assert data[0]["name"] == "general"
        assert run.call_args[0][0][:2] == ["buzz", "channels"]


def test_client_error_json():
    cfg = BuzzConfig(
        relay_url="https://example.communities.buzz.xyz",
        private_key="nsec1test",
        cli_bin="buzz",
    )
    client = BuzzClient(cfg)
    fake = MagicMock()
    fake.returncode = 3
    fake.stdout = ""
    fake.stderr = json.dumps({"error": "auth", "message": "bad key"})
    with patch("robin_igris.buzz.client.subprocess.run", return_value=fake):
        with pytest.raises(BuzzError) as ei:
            client.list_channels()
        assert "bad key" in str(ei.value)


def test_gate_with_usb_manifest(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    monkeypatch.setenv("BUZZ_PRIVATE_KEY", "nsec1test")
    from aos.manifest import Manifest

    man = Manifest.default()
    man.capabilities["buzz"] = True
    aos = tmp_path / "data" / "aos"
    aos.mkdir(parents=True)
    man.save(aos / "manifest.json")
    with patch(
        "aos.kernel.octopus_probe",
        return_value={"has_network": False, "has_display": True, "has_audio_out": True},
    ):
        out = json.loads(run_tool("buzz_send_message", {"content": "hi"}))
    assert "error" in out
