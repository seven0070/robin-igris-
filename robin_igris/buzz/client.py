"""Buzz.xyz shared workspace client — wraps buzz-cli (JSON in / JSON out).

https://buzz.xyz · https://github.com/block/buzz

Pendrive holds SOUL / PAM; Buzz holds shared tasks, messages, and artifacts
with the human team. All calls go through Manifest-gated tools.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_RELAY = "https://onboarding.communities.buzz.xyz"


@dataclass
class BuzzConfig:
    relay_url: str
    private_key: str
    cli_bin: str
    default_channel: str | None = None
    timeout_s: float = 60.0

    @classmethod
    def from_env(cls) -> "BuzzConfig":
        cli = os.getenv("BUZZ_CLI") or shutil.which("buzz") or "buzz"
        return cls(
            relay_url=(
                os.getenv("BUZZ_RELAY_URL")
                or os.getenv("BUZZ_WORKSPACE_URL")
                or DEFAULT_RELAY
            ).rstrip("/"),
            private_key=os.getenv("BUZZ_PRIVATE_KEY", ""),
            cli_bin=cli,
            default_channel=os.getenv("BUZZ_CHANNEL_ID") or None,
            timeout_s=float(os.getenv("BUZZ_TIMEOUT", "60")),
        )


class BuzzError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int = 4, raw: str = "") -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.raw = raw


class BuzzClient:
    """Thin subprocess wrapper around buzz-cli."""

    def __init__(self, config: BuzzConfig | None = None) -> None:
        self.config = config or BuzzConfig.from_env()

    def available(self) -> bool:
        return bool(shutil.which(self.config.cli_bin) or Path(self.config.cli_bin).exists())

    def configured(self) -> bool:
        return bool(self.config.private_key) and bool(self.config.relay_url)

    def run(self, *args: str, stdin_text: str | None = None) -> Any:
        if not self.config.private_key:
            raise BuzzError(
                "BUZZ_PRIVATE_KEY not set — agent needs its own Buzz keypair "
                "(create at buzz.xyz / buzz-cli auth).",
                exit_code=3,
            )
        env = os.environ.copy()
        env["BUZZ_RELAY_URL"] = self.config.relay_url
        env["BUZZ_PRIVATE_KEY"] = self.config.private_key
        cmd = [self.config.cli_bin, *args]
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_text,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_s,
                env=env,
                check=False,
            )
        except FileNotFoundError as exc:
            raise BuzzError(
                "buzz-cli not found. Install: cargo install --git "
                "https://github.com/block/buzz --path crates/buzz-cli",
                exit_code=4,
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise BuzzError(f"buzz-cli timed out after {self.config.timeout_s}s", exit_code=2) from exc

        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode != 0:
            msg = err or out or f"buzz exit {proc.returncode}"
            try:
                parsed = json.loads(err or out)
                msg = parsed.get("message") or parsed.get("error") or msg
            except json.JSONDecodeError:
                pass
            raise BuzzError(str(msg), exit_code=proc.returncode, raw=err or out)

        if not out:
            return {"ok": True}
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return {"raw": out}

    # --- high-level ops matching Manifest tools ---

    def list_channels(self) -> Any:
        return self.run("channels", "list")

    def list_messages(self, channel: str | None = None, limit: int = 20) -> Any:
        ch = channel or self.config.default_channel
        if not ch:
            raise BuzzError("channel required (pass channel or set BUZZ_CHANNEL_ID)")
        return self.run("messages", "get", "--channel", ch, "--limit", str(limit))

    def read_thread(self, event_id: str, channel: str | None = None) -> Any:
        ch = channel or self.config.default_channel
        if not ch:
            raise BuzzError("channel required")
        return self.run("messages", "thread", "--channel", ch, "--event", event_id)

    def send_message(
        self,
        content: str,
        *,
        channel: str | None = None,
        reply_to: str | None = None,
    ) -> Any:
        ch = channel or self.config.default_channel
        if not ch:
            raise BuzzError("channel required")
        args = ["messages", "send", "--channel", ch, "--content", "-"]
        if reply_to:
            args.extend(["--reply-to", reply_to])
        return self.run(*args, stdin_text=content)

    def search(self, query: str) -> Any:
        return self.run("messages", "search", "--query", query)

    def upload_artifact(self, path: str) -> Any:
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            raise BuzzError(f"artifact not found: {p}")
        return self.run("upload", "file", str(p))

    def feed(self) -> Any:
        return self.run("feed", "get")

    def list_workflows(self, channel: str | None = None) -> Any:
        ch = channel or self.config.default_channel
        if not ch:
            raise BuzzError("channel required")
        return self.run("workflows", "list", "--channel", ch)

    def request_human_input(
        self,
        question: str,
        *,
        channel: str | None = None,
        mention: str | None = None,
    ) -> Any:
        body = question.strip()
        if mention:
            body = f"{mention} — {body}"
        else:
            body = f"🙋 Need human input: {body}"
        return self.send_message(body, channel=channel)

    def status(self) -> dict[str, Any]:
        return {
            "cli_available": self.available(),
            "configured": self.configured(),
            "relay_url": self.config.relay_url,
            "default_channel": self.config.default_channel,
            "has_private_key": bool(self.config.private_key),
            "workspace": "https://buzz.xyz",
            "docs": "https://github.com/block/buzz",
        }
