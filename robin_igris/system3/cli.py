"""CLI for System 3: status, wake, heartbeat, skill bootstrap."""

from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

from robin_igris.system3.monitor import ExecutiveMonitor
from robin_igris.system3.skills import SkillBootstrap
from robin_igris.system3.cadvp import Channel, DeliveryBus


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Robin Igris System 3 (OpenLife/Sophia/OpenSkill/CADVP)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show metabolism + journal + CADVP status")

    p_wake = sub.add_parser("wake", help="Run one user/system wake through Hermes")
    p_wake.add_argument("text", help="Message / goal for this wake")

    p_hb = sub.add_parser("heartbeat", help="Run one intrinsic heartbeat wake")
    p_hb.add_argument(
        "--loop",
        action="store_true",
        help="Keep running heartbeat forever",
    )

    p_skill = sub.add_parser("skill", help="OpenSkill-style bootstrap a SKILL.md")
    p_skill.add_argument("task", help="Task description to learn")
    p_skill.add_argument("--rounds", type=int, default=3)

    p_credit = sub.add_parser("credit", help="Add budget (basic income)")
    p_credit.add_argument("amount", type=float)

    p_deliver = sub.add_parser(
        "deliver",
        help="CADVP deliver a payload (Channel A; rejects fractured cron channel)",
    )
    p_deliver.add_argument("content", help="Content to deliver")
    p_deliver.add_argument("--target", default="robin-igris")
    p_deliver.add_argument(
        "--channel",
        choices=[c.value for c in Channel],
        default=Channel.DIRECT_STORE.value,
    )

    sub.add_parser("cadvp-probe", help="Probe injection channels (CC-0)")

    args = parser.parse_args(argv)
    mon = ExecutiveMonitor()

    if args.cmd == "status":
        print(json.dumps(mon.status(), indent=2))
        return 0

    if args.cmd == "cadvp-probe":
        bus = mon.bus
        out = {ch.value: bus.probe(ch).__dict__ for ch in Channel}
        # Enum values aren't JSON-serializable in nested form — normalize
        for k, v in out.items():
            v["channel"] = v["channel"].value if hasattr(v["channel"], "value") else v["channel"]
        print(json.dumps(out, indent=2))
        return 0

    if args.cmd == "deliver":
        ch = Channel(args.channel)
        receipt = mon.bus.deliver(
            target=args.target,
            kind="manual",
            content=args.content,
            preferred_channel=ch,
        )
        print(json.dumps(receipt.to_dict(), indent=2))
        return 0 if receipt.confirmed else 2

    if args.cmd == "credit":
        mon.metabolism.credit(args.amount, reason="manual-credit")
        print(json.dumps(mon.metabolism.status(), indent=2))
        return 0

    if args.cmd == "wake":
        print(mon.wake(args.text, kind="user"))
        return 0

    if args.cmd == "heartbeat":
        if args.loop:
            print("Heartbeat loop starting… Ctrl+C to stop", file=sys.stderr)

            def on_wake(drive, prompt):
                print(f"\n--- wake drive={drive.value} ---", file=sys.stderr)
                print(mon.wake(prompt, kind="heartbeat", drive=drive))

            try:
                mon.heartbeat.run_forever(on_wake)
            except KeyboardInterrupt:
                print("\nstopped", file=sys.stderr)
            return 0
        print(mon.heartbeat_once())
        return 0

    if args.cmd == "skill":
        boot = SkillBootstrap()
        meta = boot.evolve(args.task, rounds=args.rounds)
        print(json.dumps({"path": meta["path"], "history": meta["history"]}, indent=2))
        print(f"\nWrote {meta['path']}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
