"""Structured lived experience — not raw chat logs."""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_STOP = {
    "a", "an", "the", "is", "are", "was", "were", "be", "to", "of", "and", "or",
    "in", "on", "for", "with", "what", "who", "how", "do", "you", "i", "me", "my",
    "it", "this", "that", "can", "could", "would", "please", "just", "about",
}


def extract_concepts(text: str, limit: int = 16) -> list[str]:
    toks = re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}", text or "")
    out: list[str] = []
    seen: set[str] = set()
    for t in toks:
        low = t.lower()
        if low in _STOP or low in seen:
            continue
        seen.add(low)
        out.append(low)
        if len(out) >= limit:
            break
    return out


@dataclass
class Experience:
    """One lived moment — the unit of learning for the blank seed."""

    id: str
    timestamp: float
    input: str
    my_response: str
    outcome: str  # user_satisfied | user_corrected | unclear | predicted_ok | predicted_miss
    linked_concepts: list[str]
    salience: float
    novelty: float
    prediction_error: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def score(self) -> float:
        return max(0.0, float(self.novelty) * float(self.salience))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "input": self.input,
            "my_response": self.my_response,
            "outcome": self.outcome,
            "linked_concepts": self.linked_concepts,
            "salience": self.salience,
            "novelty": self.novelty,
            "prediction_error": self.prediction_error,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Experience":
        return cls(
            id=str(data.get("id") or uuid.uuid4()),
            timestamp=float(data.get("timestamp") or time.time()),
            input=str(data.get("input") or ""),
            my_response=str(data.get("my_response") or ""),
            outcome=str(data.get("outcome") or "unclear"),
            linked_concepts=list(data.get("linked_concepts") or []),
            salience=float(data.get("salience") or 0.5),
            novelty=float(data.get("novelty") or 0.5),
            prediction_error=float(data.get("prediction_error") or 0.0),
            meta=dict(data.get("meta") or {}),
        )


@dataclass
class ExperienceLog:
    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def append(self, exp: Experience) -> Experience:
        path = self.root / f"{exp.id}.json"
        path.write_text(json.dumps(exp.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return exp

    def list_recent(self, limit: int = 200) -> list[Experience]:
        files = sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        out: list[Experience] = []
        for p in files[:limit]:
            try:
                out.append(Experience.from_dict(json.loads(p.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return out

    def count(self) -> int:
        return len(list(self.root.glob("*.json")))
