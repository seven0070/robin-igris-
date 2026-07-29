"""Grok Build integration — SpaceXAI terminal coding agent as Robin's coding sidecar.

Upstream: https://github.com/xai-org/grok-build
Install:  curl -fsSL https://x.ai/cli/install.sh | bash
Headless: grok -p "…"  (see docs/GROK_BUILD.md)

Robin / Carry do not vendor the Rust monorepo; they invoke the `grok` binary
under Manifest gates. Dual-track: Robin's mind stays on-stick; Grok Build
handles deep code edits when authenticated (XAI_API_KEY or browser OAuth).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Upstream source pin (from grok-build SOURCE_REV at integration time)
GROK_BUILD_SOURCE_REV = "2a818575225183d8ca915f5632a09b8067b5156a"
GROK_BUILD_REPO = "https://github.com/xai-org/grok-build.git"
GROK_INSTALL_SH = "https://x.ai/cli/install.sh"


@dataclass
class GrokBuildClient:
    """Thin wrapper around the `grok` CLI."""

    binary: str = "grok"
    cwd: Path | None = None
    timeout_s: float = 300.0

    @classmethod
    def detect(cls) -> "GrokBuildClient":
        env_bin = os.getenv("GROK_BIN") or os.getenv("ROBIN_GROK_BIN")
        if env_bin and Path(env_bin).exists():
            return cls(binary=env_bin)
        which = shutil.which("grok")
        # Official installer puts binary in ~/.grok/bin
        home_bin = Path.home() / ".grok" / "bin" / "grok"
        if which:
            return cls(binary=which)
        if home_bin.exists():
            return cls(binary=str(home_bin))
        return cls(binary="grok")

    def available(self) -> bool:
        return bool(shutil.which(self.binary) or Path(self.binary).exists())

    def version(self) -> str | None:
        if not self.available():
            return None
        try:
            r = subprocess.run(
                [self.binary, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            out = (r.stdout or r.stderr or "").strip()
            return out.splitlines()[0] if out else None
        except Exception:
            return None

    def status(self) -> dict[str, Any]:
        avail = self.available()
        return {
            "name": "Grok Build",
            "available": avail,
            "binary": self.binary if avail else None,
            "version": self.version() if avail else None,
            "repo": GROK_BUILD_REPO,
            "source_rev_pin": GROK_BUILD_SOURCE_REV,
            "install": f"curl -fsSL {GROK_INSTALL_SH} | bash",
            "auth": "XAI_API_KEY or browser OAuth on first `grok` launch",
            "role": "Coding sidecar for Robin / Carry (headless -p or interactive TUI)",
            "yolo": os.getenv("ROBIN_GROK_YOLO", "0") == "1",
        }

    def run_headless(
        self,
        prompt: str,
        *,
        cwd: str | Path | None = None,
        output_format: str = "plain",
        model: str | None = None,
        max_turns: int | None = None,
        yolo: bool | None = None,
        disallowed_tools: str | None = None,
        tools: str | None = None,
    ) -> dict[str, Any]:
        if not self.available():
            return {
                "ok": False,
                "error": "grok binary not found",
                "hint": f"Install: curl -fsSL {GROK_INSTALL_SH} | bash",
                "repo": GROK_BUILD_REPO,
            }
        work = Path(cwd or self.cwd or os.getcwd())
        cmd = [
            self.binary,
            "-p",
            prompt,
            "--output-format",
            output_format,
            "--cwd",
            str(work),
            "--no-auto-update",
        ]
        if model or os.getenv("ROBIN_GROK_MODEL"):
            cmd.extend(["-m", model or os.getenv("ROBIN_GROK_MODEL") or "grok-build"])
        use_yolo = yolo if yolo is not None else os.getenv("ROBIN_GROK_YOLO", "0") == "1"
        if use_yolo:
            cmd.append("--yolo")
        if max_turns is not None:
            cmd.extend(["--max-turns", str(max_turns)])
        elif os.getenv("ROBIN_GROK_MAX_TURNS"):
            cmd.extend(["--max-turns", os.environ["ROBIN_GROK_MAX_TURNS"]])
        deny = disallowed_tools or os.getenv("ROBIN_GROK_DISALLOWED_TOOLS")
        if deny:
            cmd.extend(["--disallowed-tools", deny])
        allow = tools or os.getenv("ROBIN_GROK_TOOLS")
        if allow:
            cmd.extend(["--tools", allow])

        t0 = time.time()
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                cwd=str(work),
                env={**os.environ},
            )
            stdout = (r.stdout or "").strip()
            stderr = (r.stderr or "").strip()
            result: dict[str, Any] = {
                "ok": r.returncode == 0,
                "returncode": r.returncode,
                "elapsed_s": round(time.time() - t0, 3),
                "cwd": str(work),
                "output_format": output_format,
            }
            if output_format == "json":
                try:
                    result["result"] = json.loads(stdout) if stdout else None
                except json.JSONDecodeError:
                    result["stdout"] = stdout
                    result["parse_error"] = True
            else:
                result["stdout"] = stdout
            if stderr:
                result["stderr"] = stderr[-4000:]
            return result
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"timeout after {self.timeout_s}s"}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def context_prompt(self) -> str:
        st = self.status()
        return (
            "## Grok Build (coding sidecar)\n"
            "SpaceXAI terminal coding agent — use for deep code edits when available.\n"
            "Robin remains the pendrive mind; Grok Build is the specialist coder.\n"
            f"```json\n{json.dumps(st, indent=2)}\n```\n"
        )
