"""Lived Seed — blank model that learns by experience, not backprop.

Day-1: tokenizer-scale vocabulary empty, random-ish associative graph.
Learning signal: prediction error of *your* world.
Updates: Hebbian + STDP + overnight consolidation.
Dual-track: OmniRoute answers now; this seed grows in the background.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from robin_igris.lived_seed.consolidate import consolidate
from robin_igris.lived_seed.experience import Experience, ExperienceLog, extract_concepts
from robin_igris.lived_seed.generate import generate_from_graph
from robin_igris.lived_seed.graph import AssociativeGraph
from robin_igris.lived_seed.world_model import WorldModel


@dataclass
class LivedSeed:
    root: Path
    graph: AssociativeGraph
    log: ExperienceLog
    world: WorldModel
    enabled: bool = True
    dual_track: bool = True  # OmniRoute primary; seed learns from every turn

    @classmethod
    def create(cls, usb_root: Path, *, enabled: bool = True, dual_track: bool = True) -> "LivedSeed":
        root = Path(usb_root) / "data" / "aos" / "lived_seed"
        root.mkdir(parents=True, exist_ok=True)
        return cls(
            root=root,
            graph=AssociativeGraph.load(root / "graph.json"),
            log=ExperienceLog(root / "experiences"),
            world=WorldModel.load(root / "world_model.json"),
            enabled=enabled,
            dual_track=dual_track,
        )

    def observe_turn(
        self,
        user_text: str,
        assistant_text: str,
        *,
        outcome: str = "unclear",
        salience: float | None = None,
        source: str = "omniroute",
    ) -> Experience:
        """Record a lived episode and apply online Hebbian/STDP updates."""
        concepts = extract_concepts(user_text + " " + assistant_text)
        novelty = self.graph.novelty_of(concepts)
        # salience: longer / corrected turns matter more
        sal = salience if salience is not None else min(1.0, 0.35 + len(user_text) / 400.0)
        if outcome == "user_corrected":
            sal = min(1.0, sal + 0.3)
        if outcome == "user_satisfied":
            sal = min(1.0, sal + 0.15)

        pred = self.world.predict_next_concepts(self.graph, user_text)
        err = self.world.score_error(pred, concepts)

        # Online plasticity from this moment
        inp = extract_concepts(user_text)
        out = extract_concepts(assistant_text)
        self.graph.fire(inp + out)
        self.graph.save()

        exp = Experience(
            id=str(uuid.uuid4()),
            timestamp=time.time(),
            input=user_text,
            my_response=assistant_text,
            outcome=outcome,
            linked_concepts=concepts,
            salience=round(sal, 3),
            novelty=round(novelty, 3),
            prediction_error=round(err, 3),
            meta={"source": source},
        )
        self.log.append(exp)
        return exp

    def ask(self, user_text: str) -> str:
        """Answer from lived graph only (weak until weeks of experience)."""
        return generate_from_graph(self.graph, user_text)

    def sleep(self, budget: int = 40) -> dict[str, Any]:
        report = consolidate(self.graph, self.log, budget=budget)
        # persist sleep marker
        marker = {
            "ts": time.time(),
            "report": report.to_dict(),
            "graph": {"nodes": len(self.graph.nodes), "edges": len(self.graph.edges)},
        }
        sleeps = self.root / "sleeps.jsonl"
        with sleeps.open("a", encoding="utf-8") as f:
            f.write(json.dumps(marker) + "\n")
        return marker

    def status(self) -> dict[str, Any]:
        g = self.graph.status()
        top = [
            {"name": n.name, "count": n.count, "strength": round(n.strength, 2)}
            for n in g["top_concepts"]
        ]
        return {
            "enabled": self.enabled,
            "dual_track": self.dual_track,
            "mechanism": "hebbian+stdp+consolidation",
            "not": "backprop / next-token SGD",
            "experiences": self.log.count(),
            "graph": {"nodes": g["nodes"], "edges": g["edges"], "top_concepts": top},
            "world_model": self.world.status(),
            "blank": g["nodes"] == 0,
            "note": (
                "Starts knowing nothing. OmniRoute answers now; this seed becomes "
                "unique to your shared life. No cutoff — consolidates overnight."
            ),
        }

    def context_prompt(self) -> str:
        st = self.status()
        return (
            "## Lived Seed (blank → experience learner)\n"
            "Not a fine-tune. Mechanism: Hebbian + STDP + sleep consolidation.\n"
            "Learning signal: prediction error of the user's world, not next-token loss.\n"
            "Dual-track: OmniRoute for capability now; seed grows uniquely on this pendrive.\n"
            f"```json\n{json.dumps(st, indent=2)}\n```\n"
        )
