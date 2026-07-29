"""Retrieval over paper repository + soul memory (keyword hybrid, no GPU required)."""

from __future__ import annotations

import re
from typing import Any

from aos.research.papers import PaperRepository
from aos.soul import SoulStore


def _tokens(q: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]{3,}", (q or "").lower())]


def retrieve(
    query: str,
    *,
    papers: PaperRepository | None = None,
    soul: SoulStore | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    """Return ranked snippets from papers + semantic/episodic soul entries."""
    tokens = _tokens(query)
    hits: list[dict[str, Any]] = []

    if papers is not None:
        for h in papers.search(query, limit=limit):
            p = papers.get(str(h["id"]))
            if not p:
                continue
            hits.append(
                {
                    "kind": "paper",
                    "id": p.id,
                    "title": p.title,
                    "score": h["score"] + (2 if p.promoted else 0),
                    "snippet": p.summary or p.abstract,
                    "claims": p.claims[:2],
                }
            )

    if soul is not None:
        for klass in ("semantic", "episodic", "procedural"):
            for entry in soul.list_class(klass, limit=80):  # type: ignore[arg-type]
                content = str(entry.get("content") or "")
                low = content.lower()
                score = sum(low.count(t) for t in tokens) if tokens else 0
                if score <= 0 and tokens:
                    continue
                if not tokens:
                    score = 1
                hits.append(
                    {
                        "kind": f"soul:{klass}",
                        "id": entry.get("id"),
                        "title": (entry.get("meta") or {}).get("title") or klass,
                        "score": score,
                        "snippet": content[:400],
                    }
                )

    hits.sort(key=lambda x: x.get("score", 0), reverse=True)
    return {"query": query, "hits": hits[:limit]}


def as_prompt(result: dict[str, Any]) -> str:
    import json

    return (
        "## Retrieved knowledge (papers + PAM)\n"
        "Use these as grounded context. Prefer promoted papers and linked soul entries.\n"
        f"```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```\n"
    )
