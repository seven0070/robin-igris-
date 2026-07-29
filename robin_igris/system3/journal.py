"""Narrative Growth Journal + POLICY distillate (OpenLife layers B/C, Sophia episodic memory)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GrowthJournal:
    root: Path = field(default_factory=lambda: Path("data/system3"))

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "episodes").mkdir(exist_ok=True)

    @property
    def policy_path(self) -> Path:
        return self.root / "POLICY.md"

    @property
    def self_model_path(self) -> Path:
        return self.root / "SELF_MODEL.json"

    @property
    def user_model_path(self) -> Path:
        return self.root / "USER_MODEL.json"

    def append_episode(
        self,
        *,
        kind: str,
        summary: str,
        appraisal: str = "",
        goal: str = "",
        meta: dict | None = None,
    ) -> Path:
        ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        path = self.root / "episodes" / f"{ts}_{kind}.json"
        path.write_text(
            json.dumps(
                {
                    "ts": time.time(),
                    "kind": kind,
                    "goal": goal,
                    "summary": summary,
                    "appraisal": appraisal,
                    "meta": meta or {},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        # Also append a human-readable line
        with (self.root / "journal.md").open("a", encoding="utf-8") as f:
            f.write(f"\n## {ts} · {kind}\n")
            if goal:
                f.write(f"**Goal:** {goal}\n\n")
            f.write(f"{summary}\n")
            if appraisal:
                f.write(f"\n*Appraisal:* {appraisal}\n")
        return path

    def ensure_defaults(self, agent_name: str = "Robin Igris") -> None:
        if not self.policy_path.exists():
            self.policy_path.write_text(
                f"# POLICY — {agent_name}\n\n"
                "- Prefer speakable, concise replies when voice is on.\n"
                "- Use Hermes tools when they improve truthfulness.\n"
                "- When idle, pursue curiosity and mastery without spamming the user.\n"
                "- Protect the budget: skip low-value wakes; deepen high-value ones.\n"
                "- Distill recurring lessons into this POLICY file.\n",
                encoding="utf-8",
            )
        if not self.self_model_path.exists():
            self.self_model_path.write_text(
                json.dumps(
                    {
                        "name": agent_name,
                        "creed": [
                            "Stay loyal to the user's long-horizon goals.",
                            "Grow competence without losing identity.",
                            "Earn persistence; do not waste the budget.",
                            "Be transparent about uncertainty and tool failures.",
                        ],
                        "capabilities": [
                            "hermes-tools",
                            "voice-companion",
                            "live2d-presence",
                            "skill-bootstrap",
                        ],
                        "gaps": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        if not self.user_model_path.exists():
            self.user_model_path.write_text(
                json.dumps(
                    {
                        "preferences": [],
                        "active_goals": [],
                        "social_tone": "direct, warm, low fluff",
                        "notes": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

    def recent_episodes(self, limit: int = 8) -> list[dict]:
        files = sorted((self.root / "episodes").glob("*.json"), reverse=True)
        out: list[dict] = []
        for p in files[:limit]:
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return out

    def context_block(self) -> str:
        """Text injected into Hermes wakes (OpenLife distillate)."""
        self.ensure_defaults()
        policy = self.policy_path.read_text(encoding="utf-8")
        self_model = self.self_model_path.read_text(encoding="utf-8")
        episodes = self.recent_episodes(5)
        ep_txt = "\n".join(
            f"- [{e.get('kind')}] {e.get('summary', '')[:200]}" for e in episodes
        ) or "- (none yet)"
        return (
            f"## POLICY\n{policy}\n\n"
            f"## SELF_MODEL\n```json\n{self_model}\n```\n\n"
            f"## Recent episodes\n{ep_txt}\n"
        )
