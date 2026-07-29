"""Memory-as-Compute — tiny reasoning core; knowledge lives in the graph, not weights."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aos.research.rag import retrieve
from robin_igris.lived_seed.experience import extract_concepts
from robin_igris.lived_seed.graph import AssociativeGraph


@dataclass
class MemoryHit:
    kind: str
    content: str
    score: float
    meta: dict[str, Any]


def retrieve_working_set(
    query: str,
    *,
    graph: AssociativeGraph,
    papers: Any | None = None,
    soul: Any | None = None,
    limit: int = 8,
) -> list[MemoryHit]:
    """All knowledge for this forward pass comes from memory — not baked weights."""
    hits: list[MemoryHit] = []
    concepts = extract_concepts(query)
    graph.fire(concepts)  # living activation for readout
    for name, weight in graph.associates(concepts, limit=limit):
        node = graph.nodes.get(name)
        hits.append(
            MemoryHit(
                kind="lived_graph",
                content=f"{name} (linked from {', '.join(concepts[:4])})",
                score=float(weight),
                meta={"count": getattr(node, "count", 0)},
            )
        )

    if papers is not None or soul is not None:
        rag = retrieve(query, papers=papers, soul=soul, limit=limit)
        for h in rag.get("hits") or []:
            hits.append(
                MemoryHit(
                    kind=str(h.get("kind") or "rag"),
                    content=str(h.get("snippet") or h.get("title") or ""),
                    score=float(h.get("score") or 0),
                    meta={"id": h.get("id"), "title": h.get("title")},
                )
            )

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]


def reason_over_memories(query: str, memories: list[MemoryHit]) -> str:
    """The ~100M-class 'how to think' core — compose an answer from retrieved memory only."""
    if not memories:
        return (
            "[novel/memory-as-compute] Working set empty. I do not store facts in weights. "
            "Teach me (write to memory) or let OmniRoute answer while I listen."
        )
    lines = [f"- ({m.kind}, score={m.score:.2f}) {m.content[:240]}" for m in memories[:6]]
    return (
        f"[novel/memory-as-compute] Retrieved {len(memories)} memories for: {query!r}\n"
        + "\n".join(lines)
        + "\nCompose from memory only — no pretrained world knowledge in weights."
    )
