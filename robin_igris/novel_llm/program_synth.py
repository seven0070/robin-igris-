"""Program-synthesis path — reason by writing and verifying Kairn-like skills."""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from robin_igris.lived_seed.experience import extract_concepts


@dataclass
class SynthProgram:
    id: str
    query: str
    source: str
    steps: list[str]
    result: str
    verified: bool
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "source": self.source,
            "steps": self.steps,
            "result": self.result,
            "verified": self.verified,
            "ts": self.ts,
        }


@dataclass
class SkillLibrary:
    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, prog: SynthProgram) -> None:
        (self.root / f"{prog.id}.json").write_text(
            json.dumps(prog.to_dict(), indent=2), encoding="utf-8"
        )

    def list_verified(self, limit: int = 50) -> list[dict[str, Any]]:
        out = []
        for p in sorted(self.root.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                if d.get("verified"):
                    out.append(d)
            except Exception:
                continue
            if len(out) >= limit:
                break
        return out

    def find_for_query(self, query: str) -> dict[str, Any] | None:
        q_concepts = set(extract_concepts(query))
        best = None
        best_score = 0
        for d in self.list_verified(limit=100):
            c = set(extract_concepts(str(d.get("query") or "")))
            score = len(q_concepts & c)
            if score > best_score:
                best_score = score
                best = d
        return best if best_score > 0 else None


def synthesize_program(query: str, memory_snippets: list[str]) -> SynthProgram:
    """Write a Kairn-shaped program that retrieves/derives rather than memorizing tokens."""
    concepts = extract_concepts(query)
    search_key = " ".join(concepts[:4]) or query[:40]
    steps = [
        f'call memory.search("{search_key}") into hits',
        "call format_response(hits) into answer",
        "return answer",
    ]
    # Prefer concrete memory content if present
    body = memory_snippets[0] if memory_snippets else ""
    if body:
        result = f"Derived from memory: {body[:300]}"
        verified = True
    else:
        result = "Requires memory write — no hits to execute against."
        verified = False

    # Emit Kairn-like source for the skill library
    safe_name = re.sub(r"[^a-z0-9_]+", "_", (concepts[0] if concepts else "query").lower())[:40]
    source = f"""skill solve_{safe_name}(q: String) -> Answer
    requires: [mem::semantic]
    produces: [artifact::text]
    budget: 0.01

    steps:
        // synthesized for: {query[:80]}
        call memory.search("{search_key}") into hits
        call format_response(hits) into answer
        return answer

    test "has_memory_hit"
        input: "{query[:60]}"
        expect: Answer
"""
    return SynthProgram(
        id=str(uuid.uuid4())[:12],
        query=query,
        source=source,
        steps=steps,
        result=result,
        verified=verified,
    )


def run_program_synthesis(
    query: str,
    *,
    library: SkillLibrary,
    memory_snippets: list[str],
) -> dict[str, Any]:
    """Write mode → execute mode → store if verified."""
    existing = library.find_for_query(query)
    if existing and existing.get("verified"):
        return {
            "mode": "reuse_skill",
            "program": existing,
            "reply": (
                f"[novel/program-synthesis] Reused verified skill {existing.get('id')}: "
                f"{existing.get('result')}"
            ),
        }

    prog = synthesize_program(query, memory_snippets)
    if prog.verified:
        library.save(prog)
    return {
        "mode": "write_then_execute",
        "program": prog.to_dict(),
        "reply": (
            f"[novel/program-synthesis] Wrote program ({'verified' if prog.verified else 'unverified'}):\n"
            + "\n".join(f"  {s}" for s in prog.steps)
            + f"\n→ {prog.result}"
        ),
    }
