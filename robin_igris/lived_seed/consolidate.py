"""Overnight consolidation — replay, prune, synthesize (sleep, not SGD)."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any

from robin_igris.lived_seed.experience import Experience, ExperienceLog, extract_concepts
from robin_igris.lived_seed.graph import AssociativeGraph


@dataclass
class ConsolidationReport:
    replayed: int
    pruned: int
    synthesized: int
    variations: int
    duration_s: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "replayed": self.replayed,
            "pruned": self.pruned,
            "synthesized": self.synthesized,
            "variations": self.variations,
            "duration_s": self.duration_s,
        }


def consolidate(
    graph: AssociativeGraph,
    log: ExperienceLog,
    *,
    budget: int = 40,
    synthesize: bool = True,
) -> ConsolidationReport:
    """Sleep cycle: replay high novelty×salience first, then prune + cross-link."""
    t0 = time.time()
    experiences = log.list_recent(limit=500)
    experiences.sort(key=lambda e: e.score(), reverse=True)
    replayed = 0
    variations = 0

    for exp in experiences[:budget]:
        concepts = list(exp.linked_concepts) or extract_concepts(exp.input + " " + exp.my_response)
        # reinforce in temporal order (input concepts before response concepts)
        inp = extract_concepts(exp.input)
        out = extract_concepts(exp.my_response)
        graph.fire(inp + out)
        replayed += 1

        # synthetic variation: swap a concept for a sibling associate
        if synthesize and concepts:
            base = concepts[0]
            sibs = graph.associates([base], limit=3)
            if sibs:
                variant = [sibs[0][0] if c == base else c for c in concepts]
                graph.fire(variant)
                variations += 1

    # Cross-link: concepts that co-occur across top experiences
    synthesized = 0
    if synthesize and len(experiences) >= 2:
        top = experiences[: min(20, len(experiences))]
        bags = [set(e.linked_concepts or extract_concepts(e.input)) for e in top]
        for i, a in enumerate(bags):
            for b in bags[i + 1 :]:
                shared_ctx = list(a | b)
                if len(a & b) >= 1 and len(shared_ctx) >= 2:
                    # fire union to strengthen cross-episode links
                    sample = random.sample(shared_ctx, k=min(6, len(shared_ctx)))
                    graph.fire(sample)
                    synthesized += 1

    pruned = graph.prune()
    graph.save()
    return ConsolidationReport(
        replayed=replayed,
        pruned=pruned,
        synthesized=synthesized,
        variations=variations,
        duration_s=round(time.time() - t0, 4),
    )
