"""Thin reasoning engine — memory traversal network, not a transformer.

~50M-class conceptual budget: navigate graph → assemble answer → store episode.
Never generates from parametric world knowledge. If the graph lacks the path,
it says it does not know yet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from robin_igris.lived_seed.experience import extract_concepts
from robin_igris.pendrive_native.graph_store import GraphStore, Proposition


_CAPITAL_RE = re.compile(
    r"(?i)\b(?:what(?:'s| is)|whats)\s+(?:the\s+)?capital\s+of\s+([a-zA-Z][a-zA-Z\s\-]+)\??"
)
_NAME_RE = re.compile(r"(?i)\byour\s+name\s+is\s+([a-zA-Z][a-zA-Z0-9_\- ]{1,40})")
_IS_RE = re.compile(
    r"(?i)^\s*([a-zA-Z][a-zA-Z0-9_\-]{1,40})\s+is\s+(?:the\s+)?([a-zA-Z][a-zA-Z0-9_\- ]{1,60})\s*$"
)
_TEACH_CAPITAL = re.compile(
    r"(?i)^\s*([a-zA-Z][a-zA-Z\s\-]+?)\s+is\s+the\s+capital\s+of\s+([a-zA-Z][a-zA-Z\s\-]+)\.?\s*$"
)


@dataclass
class EngineResult:
    reply: str
    found: bool
    path: list[dict[str, Any]]
    stored: list[str]
    watts_class: str = "conversation"  # ~µW-class interaction


class ThinEngine:
    """Always-on memory navigator — fits NPU cache, ~50 mW class."""

    def __init__(self, store: GraphStore) -> None:
        self.store = store

    def parse(self, text: str) -> dict[str, Any]:
        text = text.strip()
        m = _CAPITAL_RE.search(text)
        if m:
            return {"intent": "lookup", "subject": m.group(1).strip(), "relation": "capital_of"}
        m = _NAME_RE.search(text)
        if m:
            return {"intent": "teach_name", "name": m.group(1).strip()}
        m = _TEACH_CAPITAL.match(text)
        if m:
            return {
                "intent": "teach_triple",
                "subject": m.group(2).strip(),
                "relation": "capital_of",
                "object": m.group(1).strip(),
            }
        m = _IS_RE.match(text)
        if m:
            return {
                "intent": "teach_triple",
                "subject": m.group(1).strip(),
                "relation": "is_a",
                "object": m.group(2).strip(),
            }
        return {"intent": "open", "concepts": extract_concepts(text)}

    def respond(self, user_text: str) -> EngineResult:
        parsed = self.parse(user_text)
        stored: list[str] = []

        if parsed["intent"] == "teach_name":
            name = parsed["name"]
            prop = self.store.add_proposition(
                subject="this_agent",
                relation="named",
                obj=name.lower(),
                text=f"Agent name is {name}",
                kind="identity",
                confidence=1.0,
            )
            stored.append(prop.id)
            # episodic
            ep = self.store.add_proposition(
                subject="user",
                relation="said",
                obj=name.lower(),
                text=f"User said my name is {name}",
                kind="episodic",
                confidence=1.0,
            )
            stored.append(ep.id)
            return EngineResult(
                reply=f"Understood. My name is {name}. Stored in identity memory.",
                found=True,
                path=[{"etype": "named", "src": "this_agent", "dst": name.lower()}],
                stored=stored,
            )

        if parsed["intent"] == "teach_triple":
            subj = parsed["subject"].lower()
            rel = parsed["relation"]
            obj = parsed["object"].lower()
            if rel == "capital_of":
                # "Paris is the capital of France" → subject=France, object=Paris
                text = f"The capital of {parsed['subject']} is {parsed['object']}"
            else:
                text = f"{parsed['subject']} is {parsed['object']}"
            prop = self.store.add_proposition(
                subject=subj,
                relation=rel,
                obj=obj,
                text=text,
                kind="semantic",
                confidence=0.95,
            )
            stored.append(prop.id)
            self.store.hebbian_coactivate([subj, obj, rel], delta=0.1)
            return EngineResult(
                reply=f"Stored: {prop.text}",
                found=True,
                path=[{"etype": prop.relation, "src": prop.subject, "dst": prop.obj}],
                stored=stored,
            )

        if parsed["intent"] == "lookup":
            subject = parsed["subject"].lower()
            relation = parsed["relation"]
            hit = self.store.find_relation(subject, relation)
            path = self.store.traverse(subject, relation=relation, depth=1, limit=5)
            if hit:
                self._store_episode(user_text, f"The capital of {parsed['subject']} is {hit.obj}.")
                return EngineResult(
                    reply=f"The capital of {parsed['subject']} is {hit.obj}.",
                    found=True,
                    path=path or [{"etype": relation, "src": subject, "dst": hit.obj}],
                    stored=stored,
                )
            # don't guess
            self._store_episode(user_text, "I don't know yet.")
            return EngineResult(
                reply=(
                    f"I don't know yet. Teach me: "
                    f"\"[City] is the capital of {parsed['subject']}.\""
                ),
                found=False,
                path=path,
                stored=stored,
            )

        # open query — FTS + traversal assemble
        concepts = parsed.get("concepts") or extract_concepts(user_text)
        self.store.hebbian_coactivate(concepts, delta=0.03)
        hits: list[Proposition] = self.store.search_fts(user_text, limit=5)
        paths: list[dict[str, Any]] = []
        for c in concepts[:3]:
            paths.extend(self.store.traverse(c, depth=2, limit=4))
        if hits:
            lines = [h.text for h in hits[:3]]
            reply = "From memory graph:\n- " + "\n- ".join(lines)
            self._store_episode(user_text, reply)
            return EngineResult(reply=reply, found=True, path=paths[:8], stored=stored)
        if paths:
            reply = "Related paths found, but no proposition yet: " + "; ".join(
                f"{p['src']}-{p['etype']}→{p['dst']}" for p in paths[:4]
            )
            self._store_episode(user_text, reply)
            return EngineResult(reply=reply, found=True, path=paths[:8], stored=stored)

        self._store_episode(user_text, "I don't know yet.")
        return EngineResult(
            reply="I don't know yet. Tell me the fact and I will store it in the graph.",
            found=False,
            path=[],
            stored=stored,
        )

    def _store_episode(self, user_text: str, reply: str) -> None:
        self.store.add_proposition(
            subject="user",
            relation="asked",
            obj="episode",
            text=f"User: {user_text[:180]} | Engine: {reply[:180]}",
            kind="episodic",
            confidence=0.7,
        )
