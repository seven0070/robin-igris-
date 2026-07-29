"""CLI entry: python -m aos …"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aos.boot import boot, resolve_usb_root
from aos.kernel import AgentKernel
from aos.manifest import Manifest
from aos.octopus import probe


def cmd_init(root: Path) -> int:
    root = root.resolve()
    aos_data = root / "data" / "aos"
    aos_data.mkdir(parents=True, exist_ok=True)
    (root / "data" / "home").mkdir(parents=True, exist_ok=True)
    man_path = aos_data / "manifest.json"
    if not man_path.exists():
        Manifest.default().save(man_path)
        print(f"Wrote {man_path}")
    else:
        print(f"Manifest already exists: {man_path}")
    kernel = AgentKernel.create(root, manifest_path=man_path)
    tip = kernel.soul.tip()
    print(f"Soul tip: {tip.get('merkle_root')}")
    print(f"Sealed ok: {kernel.soul.verify_seal()}")
    return 0


def cmd_status(root: Path) -> int:
    k = AgentKernel.create(root)
    print(json.dumps(k.status(), indent=2, default=str))
    return 0


def cmd_probe(_root: Path) -> int:
    print(json.dumps(probe(), indent=2, default=str))
    return 0


def cmd_seal(root: Path, reason: str) -> int:
    k = AgentKernel.create(root)
    tip = k.lifecycle.seal(reason=reason)
    print(f"sealed tip={tip.get('merkle_root')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aos", description="Pendrive Agent OS")
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="USB / project root (default: ROBIN_USB_ROOT or repo)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_root(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--root",
            type=Path,
            default=None,
            dest="root_sub",
            help="USB / project root (overrides top-level --root)",
        )

    init_p = sub.add_parser("init", help="Create manifest + soul on USB root")
    add_root(init_p)
    status_p = sub.add_parser("status", help="Boot probe and print capabilities")
    add_root(status_p)
    probe_p = sub.add_parser("probe", help="Octopus hardware probe only")
    add_root(probe_p)
    seal_p = sub.add_parser("seal", help="Seal soul (intentional shutdown)")
    add_root(seal_p)
    seal_p.add_argument("--reason", default="cli-seal")
    boot_p = sub.add_parser("boot", help="Interactive Agent Shell")
    add_root(boot_p)
    once_p = sub.add_parser("boot-once", help="Boot sequence then exit")
    add_root(once_p)
    once_p.add_argument("--no-watch", action="store_true")

    args = p.parse_args(argv)
    root = resolve_usb_root(getattr(args, "root_sub", None) or args.root)

    if args.cmd == "init":
        return cmd_init(root)
    if args.cmd == "status":
        return cmd_status(root)
    if args.cmd == "probe":
        return cmd_probe(root)
    if args.cmd == "seal":
        return cmd_seal(root, args.reason)
    if args.cmd == "boot":
        return boot(usb_root=root, interactive=True, watch_unplug=True)
    if args.cmd == "boot-once":
        return boot(
            usb_root=root,
            interactive=False,
            watch_unplug=not getattr(args, "no_watch", False),
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
