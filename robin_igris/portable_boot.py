"""Portable USB boot — run Robin Igris entirely from a pendrive.

The host PC is used as display (browser) + mic/speakers only.
All state lives under the USB root detected from this file / LAUNCH scripts.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path


def detect_root() -> Path:
    """USB kit root: env ROBIN_USB_ROOT, or parent of app/, or cwd."""
    if os.getenv("ROBIN_USB_ROOT"):
        return Path(os.environ["ROBIN_USB_ROOT"]).resolve()
    # portable.py lives in app/robin_igris/ when prepared onto USB
    here = Path(__file__).resolve()
    for candidate in (here.parents[2], here.parents[1], Path.cwd()):
        marker = candidate / ".robin_usb"
        if marker.exists() or (candidate / "companion-dist").exists():
            return candidate.resolve()
    # Dev fallback: repo root
    return here.parents[1]


def apply_env(root: Path) -> None:
    root = root.resolve()
    data = root / "data"
    home = data / "home"
    for p in (data, home, data / "system3", data / "logs", root / "companion-dist"):
        p.mkdir(parents=True, exist_ok=True)

    os.environ["ROBIN_USB_ROOT"] = str(root)
    os.environ["ROBIN_DATA"] = str(data)
    os.environ.setdefault("HOME", str(home))
    os.environ.setdefault("XDG_CONFIG_HOME", str(data / "xdg"))
    os.environ.setdefault("XDG_DATA_HOME", str(data / "xdg-data"))
    # Voice + static UI
    os.environ.setdefault("VOICE_HOST", "127.0.0.1")
    os.environ.setdefault("VOICE_PORT", "8787")
    os.environ.setdefault("ROBIN_SERVE_COMPANION", "1")
    os.environ.setdefault("ROBIN_COMPANION_DIST", str(root / "companion-dist"))
    # System 3 paths
    os.environ.setdefault("ROBIN_SYSTEM3_ROOT", str(data / "system3"))
    # Load .env from USB if present
    env_file = root / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_file, override=False)
        except ImportError:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _popen(cmd: list[str], *, cwd: Path, log: Path) -> subprocess.Popen:
    log.parent.mkdir(parents=True, exist_ok=True)
    fh = log.open("a", encoding="utf-8")
    fh.write(f"\n--- spawn {cmd} @ {time.strftime('%Y-%m-%dT%H:%M:%SZ')} ---\n")
    fh.flush()
    return subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=fh,
        stderr=subprocess.STDOUT,
        env=os.environ.copy(),
    )


def start_stack(root: Path) -> list[subprocess.Popen]:
    apply_env(root)
    logs = root / "data" / "logs"
    app = root / "app"
    if not app.exists():
        # Running from repo checkout
        app = root

    procs: list[subprocess.Popen] = []
    py = sys.executable

    # Voice + companion static UI (PC display)
    procs.append(
        _popen(
            [py, "-m", "robin_igris.voice_server"],
            cwd=app,
            log=logs / "voice.log",
        )
    )

    # Optional Hermes gateway if installed under USB HOME
    hermes = Path(os.environ["HOME"]) / ".local" / "bin" / "hermes"
    if not hermes.exists():
        hermes_bin = shutil_which("hermes")
    else:
        hermes_bin = str(hermes)
    if hermes_bin and os.getenv("ROBIN_START_HERMES", "1") == "1":
        procs.append(
            _popen(
                [hermes_bin, "gateway"],
                cwd=app,
                log=logs / "hermes.log",
            )
        )

    return procs


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


def wait_http(url: str, timeout: float = 45.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status < 500:
                    return True
        except Exception:
            time.sleep(0.4)
    return False


def main() -> int:
    root = detect_root()
    apply_env(root)
    print(f"Robin Igris USB root: {root}")
    print("PC is display only — all data stays on the pendrive.")
    print("Starting voice + companion…")

    procs = start_stack(root)
    port = os.getenv("VOICE_PORT", "8787")
    url = f"http://127.0.0.1:{port}/"

    if wait_http(f"http://127.0.0.1:{port}/health"):
        print(f"Ready → {url}")
        if os.getenv("ROBIN_OPEN_BROWSER", "1") == "1":
            try:
                webbrowser.open(url)
            except Exception as exc:  # noqa: BLE001
                print(f"(browser open skipped: {exc})")
    else:
        print("Warning: health check timed out — open the URL manually:", url)

    stop = threading.Event()

    def _stop(*_a):
        stop.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _stop)  # type: ignore[attr-defined]

    print("Running. Close this window or press Ctrl+C to stop, then eject the USB.")
    try:
        while not stop.is_set():
            for p in list(procs):
                if p.poll() is not None:
                    print(f"Process exited: pid={p.pid} code={p.returncode}")
                    procs.remove(p)
            if not procs:
                break
            time.sleep(0.5)
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        time.sleep(0.5)
        for p in procs:
            if p.poll() is None:
                p.kill()
        print("Stopped. Safe to eject the USB.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
