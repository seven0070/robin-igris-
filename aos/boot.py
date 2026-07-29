"""Pendrive Agent OS boot sequence.

Order:
  1. Bind USB root (HOME / data live here)
  2. Load Manifest
  3. Octopus hardware probe
  4. Intersect → effective capabilities
  5. Open Portable Soul
  6. Enter Agent Shell (CLI)
  7. On SIGINT / unplug → seal soul → exit
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from aos.kernel import AgentKernel
from aos.lifecycle import UnplugWatcher
from aos.shell import AgentShell


def resolve_usb_root(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env = os.environ.get("ROBIN_USB_ROOT") or os.environ.get("AOS_USB_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def boot(
    *,
    usb_root: Path | None = None,
    interactive: bool = True,
    watch_unplug: bool = True,
) -> int:
    root = resolve_usb_root(usb_root)
    os.environ.setdefault("ROBIN_HOME", str(root / "data" / "home"))
    os.environ.setdefault("ROBIN_USB_ROOT", str(root))
    (root / "data" / "home").mkdir(parents=True, exist_ok=True)
    (root / "data" / "aos").mkdir(parents=True, exist_ok=True)

    kernel = AgentKernel.create(root)
    shell = AgentShell(kernel)
    print(shell.banner(), flush=True)

    sealed = {"done": False}

    def shutdown(reason: str) -> None:
        if sealed["done"]:
            return
        sealed["done"] = True
        print(f"\n[AOS] Shutdown ({reason}) — sealing soul…", flush=True)
        tip = kernel.lifecycle.seal(reason=reason)
        root_hex = tip.get("merkle_root", "")[:24]
        print(f"[AOS] Soul sealed. tip={root_hex}…  Safe to unplug.", flush=True)

    kernel.lifecycle.install_signal_handlers()
    # Replace default signal exit with our print path: seal is already via lifecycle.

    watcher: UnplugWatcher | None = None
    if watch_unplug:
        watcher = UnplugWatcher(
            usb_root=root,
            on_unplug=lambda: shutdown("unplug"),
            interval_s=1.0,
        )
        watcher.start()

    code = 0
    try:
        if not interactive:
            return 0
        while True:
            try:
                line = input("aos> ")
            except EOFError:
                shutdown("eof")
                break
            out = shell.handle_line(line)
            if out == "__QUIT__":
                shutdown("quit")
                break
            if out:
                print(out, flush=True)
    except (KeyboardInterrupt, SystemExit):
        shutdown("signal")
        code = 130
    finally:
        if watcher is not None:
            watcher.stop()
        if not sealed["done"]:
            shutdown("finally")
    return code


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Pendrive Agent OS boot")
    p.add_argument("--root", type=Path, default=None, help="USB / project root")
    p.add_argument("--once", action="store_true", help="Boot and exit (no shell)")
    p.add_argument("--no-watch", action="store_true", help="Disable unplug watcher")
    args = p.parse_args(argv)
    return boot(
        usb_root=args.root,
        interactive=not args.once,
        watch_unplug=not args.no_watch,
    )


if __name__ == "__main__":
    sys.exit(main())
