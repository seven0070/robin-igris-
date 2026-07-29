"""Predictive world simulator — choose actions by predicted outcomes, not next tokens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from robin_igris.lived_seed.experience import extract_concepts
from robin_igris.lived_seed.graph import AssociativeGraph
from robin_igris.lived_seed.world_model import WorldModel


@dataclass
class SimulatedAction:
    name: str
    description: str
    predicted_outcome: str
    value: float  # higher = better for the user


def simulate_futures(
    query: str,
    *,
    graph: AssociativeGraph,
    world: WorldModel,
    candidates: list[str] | None = None,
) -> list[SimulatedAction]:
    """Run internal what-ifs before responding."""
    seeds = extract_concepts(query)
    assoc = graph.associates(seeds, limit=5)
    strength = assoc[0][1] if assoc else 0.0
    mean_err = world.mean_error()

    actions = candidates or [
        "answer_from_memory",
        "synthesize_skill",
        "defer_to_omniroute",
        "ask_clarifying_question",
        "say_nothing",
    ]
    out: list[SimulatedAction] = []
    for name in actions:
        if name == "answer_from_memory":
            value = 0.3 + min(0.6, strength / 3.0) - mean_err * 0.2
            outcome = "user_satisfied" if strength > 0.8 else "partial"
        elif name == "synthesize_skill":
            value = 0.45 if strength < 0.5 else 0.35
            outcome = "user_satisfied_if_memory_exists"
        elif name == "defer_to_omniroute":
            # When blank/weak, deferring is high value for the user *now*
            value = 0.85 if strength < 0.4 else 0.25
            outcome = "capability_now_seed_listens"
        elif name == "ask_clarifying_question":
            value = 0.4 if len(seeds) < 2 else 0.2
            outcome = "reduce_ambiguity"
        else:  # say_nothing
            value = 0.1
            outcome = "user_figures_out_alone"
        out.append(
            SimulatedAction(
                name=name,
                description=f"Simulate action={name} given assoc_strength={strength:.2f}",
                predicted_outcome=outcome,
                value=round(value, 3),
            )
        )
    out.sort(key=lambda a: a.value, reverse=True)
    return out


def choose_action(actions: list[SimulatedAction]) -> SimulatedAction:
    return actions[0] if actions else SimulatedAction("defer_to_omniroute", "", "fallback", 0.5)


def as_dict(actions: list[SimulatedAction]) -> list[dict[str, Any]]:
    return [
        {
            "name": a.name,
            "predicted_outcome": a.predicted_outcome,
            "value": a.value,
            "description": a.description,
        }
        for a in actions
    ]
