"""OpenSkill-inspired skill bootstrap: open-world acquire → virtual verify → SKILL.md."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx


@dataclass
class SkillBootstrap:
    """
    Lightweight OpenSkill loop (arXiv:2606.06741):
      1) acquire open-world snippets (DuckDuckGo / docs URLs)
      2) draft a skill markdown artifact
      3) build simple virtual assertions (no target-task leakage)
      4) refine once if assertions fail
    """

    skills_dir: Path = field(default_factory=lambda: Path("data/system3/skills"))
    max_sources: int = 5

    def __post_init__(self) -> None:
        self.skills_dir = Path(self.skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def acquire(self, task: str) -> list[dict[str, str]]:
        """Pull grounded open-world snippets (verification anchors + knowledge)."""
        items: list[dict[str, str]] = []
        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                r = client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": task, "format": "json", "no_html": 1},
                )
                r.raise_for_status()
                data = r.json()
                if data.get("AbstractText"):
                    items.append(
                        {
                            "title": data.get("Heading") or task,
                            "snippet": data["AbstractText"],
                            "url": data.get("AbstractURL") or "",
                            "kind": "knowledge",
                        }
                    )
                for topic in (data.get("RelatedTopics") or [])[: self.max_sources]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        items.append(
                            {
                                "title": topic["Text"][:80],
                                "snippet": topic["Text"],
                                "url": topic.get("FirstURL") or "",
                                "kind": "knowledge",
                            }
                        )
                    elif isinstance(topic, dict) and "Topics" in topic:
                        for sub in topic["Topics"][:2]:
                            if sub.get("Text"):
                                items.append(
                                    {
                                        "title": sub["Text"][:80],
                                        "snippet": sub["Text"],
                                        "url": sub.get("FirstURL") or "",
                                        "kind": "knowledge",
                                    }
                                )
        except Exception as exc:  # noqa: BLE001
            items.append(
                {
                    "title": "acquire-error",
                    "snippet": str(exc),
                    "url": "",
                    "kind": "error",
                }
            )

        # Verification anchors: structural invariants we can check without target labels
        items.append(
            {
                "title": "virtual-anchor:skill-shape",
                "snippet": "Skill must include name, description, steps, and pitfalls sections.",
                "url": "",
                "kind": "verification",
            }
        )
        return items[: self.max_sources + 2]

    def virtual_assertions(self, skill_md: str) -> list[tuple[str, bool, str]]:
        """Self-built verifier (OpenSkill leakage-free style) — shape + substance checks."""
        checks: list[tuple[str, bool, str]] = []
        required = ["# ", "## Description", "## Steps", "## Pitfalls"]
        # Allow flexible headings
        flex = {
            "# ": bool(re.search(r"^#\s+\S", skill_md, re.M)),
            "## Description": bool(
                re.search(r"^##\s+(Description|Overview|Summary)", skill_md, re.M | re.I)
            ),
            "## Steps": bool(
                re.search(r"^##\s+(Steps|Procedure|Workflow)", skill_md, re.M | re.I)
            ),
            "## Pitfalls": bool(
                re.search(r"^##\s+(Pitfalls|Mistakes|Edge cases)", skill_md, re.M | re.I)
            ),
        }
        for name in required:
            ok = flex[name]
            checks.append((f"has:{name.strip()}", ok, "required section"))
        checks.append(
            (
                "min_length",
                len(skill_md.strip()) >= 200,
                "skill body should be substantive",
            )
        )
        checks.append(
            (
                "has_bullet_steps",
                bool(re.search(r"^\s*[-*1-9]", skill_md, re.M)),
                "include actionable bullets",
            )
        )
        return checks

    def draft_skill(
        self,
        task: str,
        sources: list[dict[str, str]],
        *,
        chat_fn: Any | None = None,
        prior: str | None = None,
        critique: str | None = None,
    ) -> str:
        source_block = "\n".join(
            f"- ({s['kind']}) {s['title']}: {s['snippet'][:240]} {s.get('url','')}"
            for s in sources
        )
        prompt = (
            f"Create a portable agent skill (SKILL.md) for this task:\n{task}\n\n"
            f"Open-world sources (may be noisy):\n{source_block}\n\n"
            "Output markdown ONLY with sections:\n"
            f"# <skill-name>\n## Description\n## Steps\n## Pitfalls\n## Sources\n"
        )
        if prior and critique:
            prompt += f"\nPrevious draft:\n{prior}\n\nCritique to fix:\n{critique}\n"

        if chat_fn is not None:
            return chat_fn(
                [
                    {
                        "role": "system",
                        "content": "You write concise, transferable agent skills. No target-task cheating.",
                    },
                    {"role": "user", "content": prompt},
                ]
            )

        try:
            from robin_igris.omniroute import chat_text

            return chat_text(
                [
                    {
                        "role": "system",
                        "content": "You write concise, transferable agent skills. No target-task cheating.",
                    },
                    {"role": "user", "content": prompt},
                ]
            )
        except Exception:
            try:
                from robin_igris.hermes_client import chat as hermes_chat

                return hermes_chat(
                    [
                        {
                            "role": "system",
                            "content": "You write concise, transferable agent skills. No target-task cheating.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    session_key="robin-igris-openskill",
                )
            except Exception:
                # Offline template so the loop still produces an artifact
                return (
                    f"# skill-{_slug(task)}\n\n"
                    f"## Description\nBootstrap skill for: {task}\n\n"
                    "## Steps\n"
                    "1. Restate the goal and constraints.\n"
                    "2. Gather missing facts from trusted docs.\n"
                    "3. Execute the smallest working procedure.\n"
                    "4. Verify outputs against structural checks.\n\n"
                    "## Pitfalls\n"
                    "- Do not invent APIs.\n"
                    "- Do not use hidden benchmark answers.\n\n"
                    f"## Sources\n{source_block}\n"
                )

    def evolve(
        self,
        task: str,
        *,
        rounds: int = 3,
        chat_fn: Any | None = None,
    ) -> dict[str, Any]:
        sources = self.acquire(task)
        skill = self.draft_skill(task, sources, chat_fn=chat_fn)
        history: list[dict] = []

        for j in range(max(1, rounds)):
            checks = self.virtual_assertions(skill)
            passed = all(ok for _, ok, _ in checks)
            history.append(
                {
                    "round": j,
                    "passed": passed,
                    "checks": [{"name": n, "ok": ok, "note": note} for n, ok, note in checks],
                }
            )
            if passed:
                break
            critique = "; ".join(n for n, ok, _ in checks if not ok)
            skill = self.draft_skill(
                task, sources, chat_fn=chat_fn, prior=skill, critique=critique
            )

        slug = _slug(task)
        out = self.skills_dir / f"{slug}.md"
        out.write_text(skill, encoding="utf-8")
        meta = {
            "task": task,
            "path": str(out),
            "sources": sources,
            "history": history,
            "ts": time.time(),
            "search_hint": f"https://duckduckgo.com/?q={quote_plus(task)}",
        }
        (self.skills_dir / f"{slug}.meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        return meta


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (s or "skill")[:48]
