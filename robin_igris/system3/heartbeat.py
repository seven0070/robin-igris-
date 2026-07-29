"""Heartbeat + intrinsic drives (OpenLife spontaneous activity, Sophia intrinsic motivation)."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class IntrinsicDrive(str, Enum):
    CURIOSITY = "curiosity"
    MASTERY = "mastery"
    RELATEDNESS = "relatedness"
    AUTONOMY = "autonomy"
    COHERENCE = "coherence"


DEFAULT_PROMPTS: dict[IntrinsicDrive, list[str]] = {
    IntrinsicDrive.CURIOSITY: [
        "Scan open knowledge for something novel related to our recent work and summarize one insight.",
        "Propose one question I should be curious about next, then briefly research it.",
    ],
    IntrinsicDrive.MASTERY: [
        "Pick one capability gap from SELF_MODEL and outline a short practice plan or skill to bootstrap.",
        "Rehearse a recurring task: write a tighter procedure and note what to cache next time.",
    ],
    IntrinsicDrive.RELATEDNESS: [
        "Update USER_MODEL with any inferred preferences from recent episodes. Keep it short.",
        "Draft one thoughtful check-in for the user — only if it would genuinely help; otherwise wait.",
    ],
    IntrinsicDrive.AUTONOMY: [
        "Review POLICY and propose at most one edit that would help long-term persistence.",
        "Decide whether the next wake interval should be longer or shorter, and why (budget + value).",
    ],
    IntrinsicDrive.COHERENCE: [
        "Reconcile recent episodes with creed in SELF_MODEL. Flag any drift in one paragraph.",
        "Write a three-sentence 'letter to the next self' for the next heartbeat wake.",
    ],
}


@dataclass
class Heartbeat:
    """Schedule spontaneous wakes when the user is idle (OpenLife heartbeat)."""

    interval_s: float = 900.0
    min_interval_s: float = 300.0
    max_interval_s: float = 3600.0
    last_wake: float = field(default_factory=time.time)
    drives: list[IntrinsicDrive] = field(
        default_factory=lambda: list(IntrinsicDrive)
    )

    def due(self, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        return (now - self.last_wake) >= self.interval_s

    def mark(self, now: float | None = None) -> None:
        self.last_wake = now if now is not None else time.time()

    def set_interval(self, seconds: float) -> None:
        self.interval_s = max(self.min_interval_s, min(self.max_interval_s, seconds))

    def pick_drive(self) -> IntrinsicDrive:
        return random.choice(self.drives)

    def compose_prompt(self, drive: IntrinsicDrive | None = None) -> tuple[IntrinsicDrive, str]:
        drive = drive or self.pick_drive()
        prompt = random.choice(DEFAULT_PROMPTS[drive])
        text = (
            f"[System 3 heartbeat · drive={drive.value}]\n"
            f"{prompt}\n"
            "Keep the reply short. If this wake is low value, say WAIT and conserve budget."
        )
        return drive, text

    def run_forever(
        self,
        on_wake: Callable[[IntrinsicDrive, str], None],
        *,
        should_stop: Callable[[], bool] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Blocking loop — call from a worker thread or CLI."""
        while True:
            if should_stop and should_stop():
                return
            if self.due():
                drive, prompt = self.compose_prompt()
                self.mark()
                on_wake(drive, prompt)
            sleep(min(30.0, self.interval_s / 4))
