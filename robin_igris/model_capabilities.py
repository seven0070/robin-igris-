"""LLM capability model — learn which brain is best for which job.

Local 3–7B never matches frontier clusters in raw FLOPs. The stack wins by
routing: privacy/speed → local; coding/longctx/math → best available cloud
when Manifest + WiFi allow; refine scores from observed outcomes.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Seed priors — refined by record_outcome(); not hard locks
DEFAULT_CATALOG: list[dict[str, Any]] = [
    {
        "id": "local",
        "label": "Local 3–7B (pendrive / NPU)",
        "online": False,
        "privacy": "private",
        "uncensored": True,
        "strengths": {"speed": 0.95, "privacy": 1.0, "coding": 0.45, "reasoning": 0.4, "math": 0.4, "longctx": 0.35, "vision": 0.1, "writing": 0.5},
        "notes": "Always available offline. No cloud filters. Full weights.",
    },
    {
        "id": "auto",
        "label": "OmniRoute auto",
        "online": True,
        "privacy": "cloud",
        "uncensored": False,
        "strengths": {"speed": 0.6, "privacy": 0.2, "coding": 0.75, "reasoning": 0.8, "math": 0.75, "longctx": 0.7, "vision": 0.5, "writing": 0.75},
        "notes": "OmniRoute picks among connected providers.",
    },
    {
        "id": "coding",
        "label": "Coding route",
        "online": True,
        "privacy": "cloud",
        "uncensored": False,
        "strengths": {"speed": 0.55, "privacy": 0.2, "coding": 0.95, "reasoning": 0.7, "math": 0.65, "longctx": 0.6, "vision": 0.2, "writing": 0.55},
        "notes": "Best for code/refactor/debug when online.",
    },
    {
        "id": "grok-build",
        "label": "Grok Build (xAI coding agent)",
        "online": True,
        "privacy": "cloud",
        "uncensored": False,
        "strengths": {"speed": 0.5, "privacy": 0.25, "coding": 0.98, "reasoning": 0.75, "math": 0.55, "longctx": 0.65, "vision": 0.2, "writing": 0.5},
        "notes": "SpaceXAI grok CLI — prefer for deep codebase edits when installed (GROK / XAI_API_KEY).",
    },
    {
        "id": "reasoning",
        "label": "Long reasoning route",
        "online": True,
        "privacy": "cloud",
        "uncensored": False,
        "strengths": {"speed": 0.4, "privacy": 0.2, "coding": 0.7, "reasoning": 0.95, "math": 0.8, "longctx": 0.85, "vision": 0.3, "writing": 0.8},
        "notes": "Frontier long-context reasoning when Manifest allows.",
    },
    {
        "id": "longctx",
        "label": "Long-context route",
        "online": True,
        "privacy": "cloud",
        "uncensored": False,
        "strengths": {"speed": 0.35, "privacy": 0.2, "coding": 0.55, "reasoning": 0.75, "math": 0.55, "longctx": 0.98, "vision": 0.3, "writing": 0.7},
        "notes": "Papers, transcripts, large docs.",
    },
    {
        "id": "cheap",
        "label": "Cheap / bulk route",
        "online": True,
        "privacy": "cloud",
        "uncensored": False,
        "strengths": {"speed": 0.85, "privacy": 0.25, "coding": 0.4, "reasoning": 0.4, "math": 0.35, "longctx": 0.4, "vision": 0.2, "writing": 0.45},
        "notes": "Classification and bulk jobs.",
    },
    {
        "id": "vision",
        "label": "Vision route",
        "online": True,
        "privacy": "cloud",
        "uncensored": False,
        "strengths": {"speed": 0.5, "privacy": 0.2, "coding": 0.35, "reasoning": 0.55, "math": 0.3, "longctx": 0.5, "vision": 0.95, "writing": 0.5},
        "notes": "Images / screenshots when a vision provider is connected.",
    },
]

TASK_TO_STRENGTH = {
    "coding": "coding",
    "reasoning": "reasoning",
    "longctx": "longctx",
    "cheap": "speed",
    "math": "math",
    "vision": "vision",
    "writing": "writing",
    "privacy": "privacy",
    "auto": "reasoning",
}


@dataclass
class CapabilityModel:
    """Persistent scores over OmniRoute model ids / aliases."""

    path: Path
    catalog: list[dict[str, Any]] = field(default_factory=list)
    outcomes: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, root: Path) -> "CapabilityModel":
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        path = root / "model_capabilities.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                path=path,
                catalog=list(data.get("catalog") or DEFAULT_CATALOG),
                outcomes=list(data.get("outcomes") or [])[-500:],
            )
        m = cls(path=path, catalog=[dict(x) for x in DEFAULT_CATALOG], outcomes=[])
        m.save()
        return m

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"catalog": self.catalog, "outcomes": self.outcomes[-500:], "updated": time.time()},
                indent=2,
            ),
            encoding="utf-8",
        )

    def get(self, model_id: str) -> dict[str, Any] | None:
        for c in self.catalog:
            if c.get("id") == model_id:
                return c
        return None

    def rank(
        self,
        task_kind: str,
        *,
        allow_cloud: bool,
        prefer_uncensored: bool = False,
        prefer_privacy: bool = False,
    ) -> list[dict[str, Any]]:
        strength_key = TASK_TO_STRENGTH.get(task_kind, "reasoning")
        scored: list[dict[str, Any]] = []
        for c in self.catalog:
            if c.get("online") and not allow_cloud:
                continue
            if prefer_uncensored and not c.get("uncensored") and allow_cloud:
                # still list cloud, but local gets boost below
                pass
            strengths = c.get("strengths") or {}
            base = float(strengths.get(strength_key, 0.3))
            # Empirical nudge from outcomes
            base += self._empirical_bonus(str(c.get("id")), task_kind)
            if prefer_privacy or prefer_uncensored:
                if c.get("privacy") == "private":
                    base += 0.25
                if c.get("uncensored"):
                    base += 0.15
            if not allow_cloud and c.get("online"):
                continue
            scored.append({**c, "score": round(base, 4)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def best(
        self,
        task_kind: str,
        *,
        allow_cloud: bool,
        prefer_uncensored: bool = False,
        prefer_privacy: bool = False,
    ) -> dict[str, Any]:
        ranked = self.rank(
            task_kind,
            allow_cloud=allow_cloud,
            prefer_uncensored=prefer_uncensored,
            prefer_privacy=prefer_privacy,
        )
        if not ranked:
            return dict(DEFAULT_CATALOG[0])
        return ranked[0]

    def _empirical_bonus(self, model_id: str, task_kind: str) -> float:
        relevant = [o for o in self.outcomes if o.get("model") == model_id and o.get("task") == task_kind]
        if not relevant:
            return 0.0
        wins = sum(1 for o in relevant if o.get("ok"))
        return (wins / len(relevant) - 0.5) * 0.3

    def record_outcome(self, model: str, task: str, ok: bool, note: str = "") -> None:
        self.outcomes.append(
            {"ts": time.time(), "model": model, "task": task, "ok": bool(ok), "note": note[:200]}
        )
        self.outcomes = self.outcomes[-500:]
        self.save()

    def status(self) -> dict[str, Any]:
        return {
            "models": [
                {
                    "id": c.get("id"),
                    "online": c.get("online"),
                    "uncensored": c.get("uncensored"),
                    "privacy": c.get("privacy"),
                    "top_strengths": sorted(
                        (c.get("strengths") or {}).items(), key=lambda kv: kv[1], reverse=True
                    )[:3],
                }
                for c in self.catalog
            ],
            "outcome_count": len(self.outcomes),
            "local_model_env": os.getenv("OMNIROUTE_LOCAL_MODEL") or "local",
        }

    def context_prompt(self) -> str:
        return (
            "## LLM capability model\n"
            "Route by learned strengths. Local = private + uncensored. Cloud = Manifest/WiFi gated.\n"
            f"```json\n{json.dumps(self.status(), indent=2)}\n```\n"
        )
