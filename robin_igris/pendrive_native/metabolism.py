"""Metabolism — learning as continuous low-power life, not training runs.

Power classes (Carry Micro budgets):
  conversation ~ µW–mW per turn (Hebbian edge nudge)
  idle         ~ 10 mW (silent replay / synthetic probes)
  overnight    ~ 1 W for 30–60 min (prune, promote, abstract)
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any

from robin_igris.pendrive_native.graph_store import GraphStore


POWER_MW = {
    "conversation": 0.001,  # ~1 µW class placeholder as mW
    "idle": 10.0,
    "overnight": 1000.0,
}


@dataclass
class MetabolismReport:
    phase: str
    actions: list[str]
    pruned: int
    synthesized: int
    replayed: int
    power_mw: float
    duration_s: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "actions": self.actions,
            "pruned": self.pruned,
            "synthesized": self.synthesized,
            "replayed": self.replayed,
            "power_mw": self.power_mw,
            "duration_s": self.duration_s,
        }


def idle_tick(store: GraphStore, *, budget: int = 5) -> MetabolismReport:
    """Silent replay while user thinks — ~10 mW class."""
    t0 = time.time()
    actions: list[str] = []
    props = store._conn.execute(
        "SELECT * FROM propositions ORDER BY ts DESC LIMIT ?",
        (budget * 3,),
    ).fetchall()
    replayed = 0
    for row in props[:budget]:
        store.hebbian_coactivate([row["subject"], row["object"], row["relation"]], delta=0.02)
        replayed += 1
        actions.append(f"replay:{row['id'][:8]}")
    # synthetic variation
    synthesized = 0
    if len(props) >= 2:
        a, b = random.sample(list(props[: min(10, len(props))]), 2)
        store.link(a["subject"], b["subject"], "semantic", delta=0.01)
        synthesized = 1
        actions.append("synthetic_combination")
    return MetabolismReport(
        phase="idle",
        actions=actions,
        pruned=0,
        synthesized=synthesized,
        replayed=replayed,
        power_mw=POWER_MW["idle"],
        duration_s=round(time.time() - t0, 4),
    )


def overnight(store: GraphStore, *, max_age_days: float = 90.0) -> MetabolismReport:
    """Full consolidation — ~1 W class when charging / unused."""
    t0 = time.time()
    actions: list[str] = ["full_graph_pass"]
    # promote frequent edges
    store._conn.execute(
        """
        UPDATE edges SET weight = MIN(5.0, weight + 0.05)
        WHERE hits > 5
        """
    )
    store._conn.commit()
    actions.append("promote_frequent")
    pruned = store.prune(min_weight=0.05, max_age_days=max_age_days)
    actions.append(f"prune:{pruned}")

    # synthesize capital-city abstraction if ≥2 capital_of edges
    caps = store._conn.execute(
        "SELECT src, dst FROM edges WHERE etype = 'capital_of' LIMIT 20"
    ).fetchall()
    synthesized = 0
    if len(caps) >= 2:
        store.add_proposition(
            subject="capital_cities",
            relation="is_a",
            obj="abstraction",
            text=(
                "Abstraction: capital cities — inferred from "
                + ", ".join(f"{r['dst']} of {r['src']}" for r in caps[:5])
            ),
            kind="semantic",
            confidence=0.8,
        )
        for r in caps:
            store.link(r["dst"], "capital_cities", "is_a", delta=0.1)
        synthesized = 1
        actions.append("synthesize:capital_cities")

    # rewrite soul tip marker (identity metabolism)
    counts = store.counts()
    store.set_meta(
        "soul_rewrite",
        {
            "ts": time.time(),
            "note": "Consolidation rewrote self-model markers from lived graph.",
            "counts": counts,
        },
    )
    actions.append("rewrite_soul_marker")

    # replay compressed episodes
    replayed = 0
    eps = store._conn.execute(
        "SELECT subject, object, relation FROM propositions WHERE kind = 'episodic' ORDER BY ts DESC LIMIT 40"
    ).fetchall()
    for row in eps:
        store.hebbian_coactivate([row["subject"], row["object"]], delta=0.015)
        replayed += 1

    store.set_meta("last_overnight", time.time())
    return MetabolismReport(
        phase="overnight",
        actions=actions,
        pruned=pruned,
        synthesized=synthesized,
        replayed=replayed,
        power_mw=POWER_MW["overnight"],
        duration_s=round(time.time() - t0, 4),
    )
