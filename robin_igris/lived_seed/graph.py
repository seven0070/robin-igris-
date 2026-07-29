"""Associative concept graph with Hebbian + STDP plasticity — not backprop."""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ConceptNode:
    name: str
    activation: float = 0.0
    strength: float = 1.0  # how established
    last_fired: float = 0.0
    count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "activation": self.activation,
            "strength": self.strength,
            "last_fired": self.last_fired,
            "count": self.count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConceptNode":
        return cls(
            name=str(data["name"]),
            activation=float(data.get("activation") or 0),
            strength=float(data.get("strength") or 1),
            last_fired=float(data.get("last_fired") or 0),
            count=int(data.get("count") or 0),
        )


@dataclass
class Edge:
    src: str
    dst: str
    weight: float = 0.1
    forward_hits: int = 0
    backward_hits: int = 0

    def key(self) -> str:
        return f"{self.src}->{self.dst}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "src": self.src,
            "dst": self.dst,
            "weight": self.weight,
            "forward_hits": self.forward_hits,
            "backward_hits": self.backward_hits,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Edge":
        return cls(
            src=str(data["src"]),
            dst=str(data["dst"]),
            weight=float(data.get("weight") or 0.1),
            forward_hits=int(data.get("forward_hits") or 0),
            backward_hits=int(data.get("backward_hits") or 0),
        )


@dataclass
class AssociativeGraph:
    """Lived internal representations — fire-together / wire-together + STDP."""

    path: Path
    nodes: dict[str, ConceptNode] = field(default_factory=dict)
    edges: dict[str, Edge] = field(default_factory=dict)
    hebbian_lr: float = 0.08
    stdp_lr: float = 0.05
    decay: float = 0.002
    max_weight: float = 5.0

    @classmethod
    def load(cls, path: Path, **kwargs: Any) -> "AssociativeGraph":
        path = Path(path)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            g = cls(path=path, **kwargs)
            g.nodes = {k: ConceptNode.from_dict(v) for k, v in (data.get("nodes") or {}).items()}
            g.edges = {k: Edge.from_dict(v) for k, v in (data.get("edges") or {}).items()}
            return g
        g = cls(path=path, **kwargs)
        g.save()
        return g

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {
                    "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
                    "edges": {k: v.to_dict() for k, v in self.edges.items()},
                    "updated": time.time(),
                    "mechanism": "hebbian+stdp",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def ensure(self, name: str) -> ConceptNode:
        name = name.lower().strip()
        if name not in self.nodes:
            self.nodes[name] = ConceptNode(name=name, last_fired=time.time())
        return self.nodes[name]

    def fire(self, names: list[str], now: float | None = None) -> None:
        now = now if now is not None else time.time()
        # decay all lightly
        for n in self.nodes.values():
            n.activation *= 0.85
        ordered = [self.ensure(n) for n in names if n]
        for i, node in enumerate(ordered):
            node.activation = min(1.0, node.activation + 0.6)
            node.count += 1
            node.strength = min(10.0, node.strength + 0.02)
            prev_fire = node.last_fired
            node.last_fired = now
            # Hebbian with co-active peers
            for other in ordered:
                if other.name == node.name:
                    continue
                self._hebbian(node.name, other.name)
            # STDP: earlier concepts in the list precede later ones
            for j in range(i):
                earlier = ordered[j]
                self._stdp(earlier.name, node.name, dt=max(0.001, (i - j) * 0.05))
            _ = prev_fire

    def _edge(self, src: str, dst: str) -> Edge:
        key = f"{src}->{dst}"
        if key not in self.edges:
            self.edges[key] = Edge(src=src, dst=dst)
        return self.edges[key]

    def _hebbian(self, a: str, b: str) -> None:
        # Symmetric co-activation
        for src, dst in ((a, b), (b, a)):
            e = self._edge(src, dst)
            e.weight = min(self.max_weight, e.weight + self.hebbian_lr)
            e.forward_hits += 1

    def _stdp(self, pre: str, post: str, dt: float) -> None:
        """If pre consistently precedes post, strengthen pre→post, weaken reverse."""
        fwd = self._edge(pre, post)
        # classic STDP-ish: potentiation when pre before post
        delta = self.stdp_lr * math.exp(-dt)
        fwd.weight = min(self.max_weight, fwd.weight + delta)
        fwd.forward_hits += 1
        rev = self._edge(post, pre)
        rev.weight = max(0.01, rev.weight - delta * 0.5)
        rev.backward_hits += 1

    def prune(self, min_weight: float = 0.05, max_unused_days: float = 30.0) -> int:
        now = time.time()
        removed = 0
        for key in list(self.edges.keys()):
            e = self.edges[key]
            e.weight = max(0.01, e.weight * (1.0 - self.decay))
            if e.weight < min_weight and e.forward_hits + e.backward_hits < 3:
                del self.edges[key]
                removed += 1
        for name in list(self.nodes.keys()):
            n = self.nodes[name]
            age_days = (now - n.last_fired) / 86400.0 if n.last_fired else 999
            if n.count < 2 and age_days > max_unused_days and n.strength < 1.2:
                # remove isolated weak nodes
                for key in list(self.edges.keys()):
                    if key.startswith(f"{name}->") or key.endswith(f"->{name}"):
                        del self.edges[key]
                del self.nodes[name]
                removed += 1
        return removed

    def associates(self, seed: list[str], limit: int = 8) -> list[tuple[str, float]]:
        scores: dict[str, float] = {}
        for s in seed:
            s = s.lower()
            if s not in self.nodes:
                continue
            for e in self.edges.values():
                if e.src == s:
                    scores[e.dst] = scores.get(e.dst, 0.0) + e.weight * self.nodes[s].activation
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return [(n, w) for n, w in ranked if n not in {x.lower() for x in seed}][:limit]

    def novelty_of(self, concepts: list[str]) -> float:
        if not concepts:
            return 0.5
        known = sum(1 for c in concepts if c.lower() in self.nodes and self.nodes[c.lower()].count > 0)
        return max(0.0, min(1.0, 1.0 - known / max(1, len(concepts))))

    def status(self) -> dict[str, Any]:
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "mechanism": "hebbian+stdp",
            "top_concepts": sorted(
                self.nodes.values(), key=lambda n: n.count, reverse=True
            )[:10],
        }
