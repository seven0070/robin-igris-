"""Carry Micro Hardware — native RAM + power/thermal/display adaptability."""

import json
from pathlib import Path

from aos.adaptability import AdaptabilityContract, BOARD_PROFILES, POWER_PROFILES
from aos.kernel import AgentKernel


def test_board_profiles_exist():
    assert "carry-micro-v0-sim" in BOARD_PROFILES
    assert "carry-micro-rk3588s" in BOARD_PROFILES
    assert POWER_PROFILES["powersave"]["max_w"] < POWER_PROFILES["turbo"]["max_w"]


def test_powersave_on_usb2(monkeypatch):
    monkeypatch.setenv("CARRY_POWER_SOURCE", "usb2")
    monkeypatch.delenv("CARRY_HOST_BATTERY", raising=False)
    c = AdaptabilityContract.from_manifest_raw({"adaptability": {"board": "carry-micro-v0-sim"}})
    st = c.probe()
    assert st.power["profile"] == "powersave"
    assert st.behavior["patient_mode"] is True
    assert st.behavior["allow_heavy_compute"] is False


def test_turbo_demoted_on_host_battery(monkeypatch):
    monkeypatch.setenv("CARRY_POWER_SOURCE", "pd")
    monkeypatch.setenv("CARRY_HOST_BATTERY", "1")
    c = AdaptabilityContract.from_manifest_raw(
        {"adaptability": {"power": {"profile": "auto", "respect_host_battery": True}}}
    )
    st = c.probe()
    assert st.power["profile"] == "standard"
    assert st.behavior["voice"] == "quieter"


def test_thermal_throttle(monkeypatch):
    monkeypatch.setenv("CARRY_THERMAL_C", "85")
    monkeypatch.setenv("CARRY_POWER_SOURCE", "usb3")
    c = AdaptabilityContract.from_manifest_raw(
        {"adaptability": {"thermal": {"mode": "performance", "throttle_c": 80}}}
    )
    st = c.probe()
    assert st.thermal["throttled"] is True
    assert st.scheduler["defer_heavy"] is True
    assert st.behavior["allow_heavy_compute"] is False


def test_display_paths(monkeypatch):
    monkeypatch.setenv("CARRY_DISPLAY_PATH", "headless")
    c = AdaptabilityContract.from_manifest_raw({})
    st = c.probe()
    assert st.display["path"] == "headless"
    assert st.display["avatar_quality"] == "none"


def test_native_ram_envelope(monkeypatch):
    monkeypatch.setenv("CARRY_NATIVE_RAM_MB", "8192")
    monkeypatch.setenv("CARRY_BOARD", "carry-micro-rk3588s")
    c = AdaptabilityContract.from_manifest_raw({})
    st = c.probe()
    assert st.native_ram["capacity_mb"] == 8192
    assert st.native_ram["private"] is True
    assert "LPDDR" in st.native_ram["backed_by"]


def test_enclave_tamper_wipes_identity(monkeypatch):
    monkeypatch.setenv("CARRY_ENCLAVE", "1")
    monkeypatch.setenv("CARRY_TAMPER", "1")
    c = AdaptabilityContract.from_manifest_raw(
        {"adaptability": {"enclave": {"tamper_wipe": True, "required": True}}}
    )
    st = c.probe()
    assert st.enclave["tampered"] is True
    assert st.enclave["identity_alive"] is False


def test_kernel_wires_adaptability(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    monkeypatch.setenv("CARRY_POWER_SOURCE", "usb3")
    k = AgentKernel.create(tmp_path)
    assert k.adaptability is not None
    ctx = k.boot_context()
    assert "Carry Micro Hardware" in ctx
    assert "native_ram" in k.status()["adaptability"]


def test_shell_adapt_command(tmp_path: Path, monkeypatch):
    (tmp_path / ".robin_usb").touch()
    monkeypatch.setenv("ROBIN_USB_ROOT", str(tmp_path))
    monkeypatch.setenv("CARRY_DISPLAY_PATH", "wifi_ui")
    from aos.shell import AgentShell

    k = AgentKernel.create(tmp_path)
    shell = AgentShell(k)
    out = json.loads(shell.handle_line(":adapt"))
    assert out["display"]["path"] == "wifi_ui"
