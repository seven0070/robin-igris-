"""Predictive world model — learning signal is prediction error of *your* life."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from robin_igris.lived_seed.experience import extract_concepts
from robin_igris.lived_seed.graph import AssociativeGraph


@dataclass
class Prediction:
    kind: str
    predicted: list[str]
    confidence: float
    actual: list[str] = field(default_factory=list)
    error: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "predicted": self.predicted,
            "confidence": self.confidence,
            "actual": self.actual,
            "error": self.error,
        }


@dataclass
class WorldModel:
    """Predict next concepts / outcomes from the associative graph — not next tokens."""

    path: Path
    stats: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "WorldModel":
        path = Path(path)
        stats: dict[str, Any] = {"predictions": 0, "total_error": 0.0, "history": []}
        if path.exists():
            stats = json.loads(path.read_text(encoding="utf-8"))
        return cls(path=path, stats=stats)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.stats, indent=2), encoding="utf-8")

    def predict_next_concepts(self, graph: AssociativeGraph, user_text: str) -> Prediction:
        seeds = extract_concepts(user_text)
        graph.fire(seeds)  # temporary activation for readout
        assoc = graph.associates(seeds, limit=6)
        predicted = [a for a, _ in assoc]
        conf = min(1.0, sum(w for _, w in assoc) / 5.0) if assoc else 0.05
        return Prediction(kind="next_concepts", predicted=predicted, confidence=conf)

    def predict_outcome(self, graph: AssociativeGraph, user_text: str) -> Prediction:
        seeds = extract_concepts(user_text)
        # crude: if strong relatedness edges exist, expect satisfied
        assoc = graph.associates(seeds, limit=3)
        if assoc and assoc[0][1] > 1.0:
            predicted = ["user_satisfied"]
            conf = min(0.9, 0.3 + assoc[0][1] / 5.0)
        elif not assoc:
            predicted = ["unclear"]
            conf = 0.2
        else:
            predicted = ["user_satisfied"]
            conf = 0.4
        return Prediction(kind="outcome", predicted=predicted, confidence=conf)

    def score_error(self, pred: Prediction, actual: list[str] | str) -> float:
        act = [actual] if isinstance(actual, str) else list(actual)
        pred.actual = act
        if not pred.predicted:
            err = 1.0
        else:
            overlap = len(set(x.lower() for x in pred.predicted) & set(x.lower() for x in act))
            err = 1.0 - (overlap / max(len(pred.predicted), 1))
        pred.error = err
        self.stats["predictions"] = int(self.stats.get("predictions") or 0) + 1
        self.stats["total_error"] = float(self.stats.get("total_error") or 0) + err
        hist = list(self.stats.get("history") or [])
        hist.append({"ts": time.time(), **pred.to_dict()})
        self.stats["history"] = hist[-200:]
        self.save()
        return err

    def mean_error(self) -> float:
        n = int(self.stats.get("predictions") or 0)
        if n <= 0:
            return 1.0
        return float(self.stats.get("total_error") or 0) / n

    def status(self) -> dict[str, Any]:
        return {
            "predictions": self.stats.get("predictions", 0),
            "mean_error": round(self.mean_error(), 4),
            "recent": (self.stats.get("history") or [])[-5:],
        }
