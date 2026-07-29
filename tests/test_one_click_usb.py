"""One-click USB installer entrypoints exist and are documented."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_install_entrypoints_exist() -> None:
    assert (ROOT / "INSTALL_TO_USB.bat").is_file()
    assert (ROOT / "INSTALL_TO_USB.sh").is_file()
    assert (ROOT / "INSTALL_TO_USB.command").is_file()
    assert (ROOT / "scripts" / "one-click-usb.sh").is_file()
    assert (ROOT / "scripts" / "one-click-usb.ps1").is_file()
    assert (ROOT / "scripts" / "prepare-usb.sh").is_file()
    assert (ROOT / "scripts" / "prepare-usb.ps1").is_file()
    assert (ROOT / "docs" / "ONE_CLICK_USB.md").is_file()


def test_install_sh_invokes_one_click() -> None:
    text = (ROOT / "INSTALL_TO_USB.sh").read_text(encoding="utf-8")
    assert "one-click-usb.sh" in text


def test_one_click_sh_calls_prepare() -> None:
    text = (ROOT / "scripts" / "one-click-usb.sh").read_text(encoding="utf-8")
    assert "prepare-usb.sh" in text
    assert "ROBIN_USB_DEST" in text


def test_one_click_ps1_calls_prepare() -> None:
    text = (ROOT / "scripts" / "one-click-usb.ps1").read_text(encoding="utf-8")
    assert "prepare-usb.ps1" in text
    assert "ROBIN_USB_DEST" in text


def test_readme_mentions_one_click() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "INSTALL_TO_USB" in readme
    assert "ONE_CLICK_USB" in readme
