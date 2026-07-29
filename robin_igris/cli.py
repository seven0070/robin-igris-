"""CLI entrypoint for Robin Igris."""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from robin_igris.agent import Agent


def run_cli(prompt: str | None = None) -> int:
    load_dotenv()
    agent = Agent(
        on_tool=lambda name, args, _result: print(
            f"  ⚙ {name}({args})", file=sys.stderr
        )
    )

    if prompt:
        print(agent.chat(prompt))
        return 0

    print(f"{agent.name} ready. Type /reset, /quit, or a message.\n")
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in {"/quit", "/exit", "quit", "exit"}:
            return 0
        if line == "/reset":
            agent.reset()
            print("(memory cleared)")
            continue
        try:
            reply = agent.chat(line)
        except Exception as exc:  # noqa: BLE001
            print(f"error: {exc}", file=sys.stderr)
            continue
        print(f"{agent.name}> {reply}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Robin Igris AI agent")
    parser.add_argument("-p", "--prompt", help="One-shot prompt (non-interactive)")
    args = parser.parse_args()
    raise SystemExit(run_cli(args.prompt))


if __name__ == "__main__":
    main()
