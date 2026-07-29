"""Lifecycle: unplug / SIGTERM is intentional shutdown, not a crash."""

from __future__ import annotations

import atexit
import json
import signal
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from aos.soul import SoulStore


@dataclass
class Lifecycle:
    soul: SoulStore
    log_path: Path | None = None
    on_shutdown: list[Callable[[], None]] = field(default_factory=list)
    _sealed: bool = False
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        if self.log_path is None:
            self.log_path = self.soul.root / "meta" / "lifecycle.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log("boot", "lifecycle armed — unplug is intentional shutdown")

    def _log(self, event: str, detail: str) -> None:
        assert self.log_path is not None
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps({"ts": time.time(), "event": event, "detail": detail}) + "\n"
            )

    def register(self, fn: Callable[[], None]) -> None:
        self.on_shutdown.append(fn)

    def seal(self, reason: str = "shutdown") -> dict:
        with self._lock:
            if self._sealed:
                return self.soul.tip()
            self._log("seal_begin", reason)
            for fn in self.on_shutdown:
                try:
                    fn()
                except Exception as exc:  # noqa: BLE001
                    self._log("seal_hook_error", str(exc))
            tip = self.soul._update_tip()
            self.soul.append(
                "episodic",
                f"Shutdown sealed ({reason}). Merkle tip {tip['merkle_root'][:16]}…",
                meta={"reason": reason, "tip": tip["merkle_root"]},
            )
            tip = self.soul._update_tip()
            self._sealed = True
            self._log("seal_done", tip["merkle_root"])
            return tip

    def install_signal_handlers(self) -> None:
        def _handler(signum, _frame):
            name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
            self.seal(reason=f"signal:{name}")
            raise SystemExit(0)

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, _handler)
            except Exception:
                pass
        if hasattr(signal, "SIGBREAK"):
            try:
                signal.signal(signal.SIGBREAK, _handler)  # type: ignore[attr-defined]
            except Exception:
                pass
        atexit.register(lambda: self.seal("atexit"))


@dataclass
class UnplugWatcher:
    """Poll that the USB root is still mounted; unplug → intentional shutdown."""

    usb_root: Path
    on_unplug: Callable[[], None]
    interval_s: float = 1.0
    marker_name: str = ".robin_usb"
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = field(default=None, init=False)

    def start(self) -> None:
        root = Path(self.usb_root)
        # Prefer marker file; fall back to root existing
        marker = root / self.marker_name
        self._probe_path = marker if marker.exists() else root

        def _loop() -> None:
            while not self._stop.wait(self.interval_s):
                try:
                    if not self._probe_path.exists():
                        self.on_unplug()
                        return
                except OSError:
                    self.on_unplug()
                    return

        self._thread = threading.Thread(target=_loop, name="aos-unplug-watch", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
