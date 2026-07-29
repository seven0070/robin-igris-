"""CLI for System 3: status, wake, heartbeat, skill bootstrap."""

from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

from robin_igris.system3.monitor import ExecutiveMonitor
from robin_igris.system3.skills import SkillBootstrap


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Robin Igris System 3 (OpenLife/Sophia/OpenSkill)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show metabolism + journal status")

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

    args = parser.parse_args(argv)
    mon = ExecutiveMonitor()

    if args.cmd == "status":
        print(json.dumps(mon.status(), indent=2))
        return 0

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
