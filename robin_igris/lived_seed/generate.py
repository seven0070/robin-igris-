"""Response generation from the lived associative graph — blank until experienced."""

from __future__ import annotations

from robin_igris.lived_seed.experience import extract_concepts
from robin_igris.lived_seed.graph import AssociativeGraph


def generate_from_graph(graph: AssociativeGraph, user_text: str) -> str:
    """Honest blank-seed reply: only what it has lived. No internet priors."""
    seeds = extract_concepts(user_text)
    if not graph.nodes:
        return (
            "[lived-seed] I am blank. I have no pretraining. "
            "Tell me things; overnight I consolidate. OmniRoute can answer for now."
        )

    known = [s for s in seeds if s in graph.nodes]
    if not known:
        return (
            "[lived-seed] I don't know these concepts yet: "
            + ", ".join(seeds[:8] or ["(none)"])
            + ". Teach me, or let OmniRoute answer while I listen and store the episode."
        )

    graph.fire(known)
    assoc = graph.associates(known, limit=8)
    links = ", ".join(f"{n}({w:.2f})" for n, w in assoc) if assoc else "(no strong links yet)"
    strengths = ", ".join(
        f"{n}:{graph.nodes[n].count}×" for n in known if n in graph.nodes
    )
    return (
        f"[lived-seed] From lived memory only — activated: {strengths}. "
        f"Associates: {links}. "
        "I predict from our shared life, not from the internet."
    )
