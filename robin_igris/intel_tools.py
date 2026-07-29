"""Intelligence stack tools — papers, RAG, capability model, curation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from aos.research.ingest import ingest_auto
from robin_igris.intelligence import IntelligenceStack


def _stack() -> IntelligenceStack:
    root = os.getenv("ROBIN_USB_ROOT") or os.getenv("AOS_USB_ROOT") or "."
    return IntelligenceStack.create(Path(root))


def _ok(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _err(msg: str, **extra: Any) -> str:
    return json.dumps({"error": msg, **extra}, ensure_ascii=False)


def intel_status() -> str:
    return _ok(_stack().status())


def paper_ingest(ref: str = "", text: str = "", title: str = "", tags: str = "") -> str:
    """Ingest a paper/OSINT note. Offline: pass text=. Online arxiv/url needs network."""
    stack = _stack()
    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    allow_net = os.getenv("ROBIN_FORCE_OFFLINE", "0") != "1"
    try:
        from aos.kernel import AgentKernel

        root = os.getenv("ROBIN_USB_ROOT") or os.getenv("AOS_USB_ROOT")
        if root:
            k = AgentKernel.create(Path(root))
            allow_net = bool(k.runtime.effective.get("network")) and allow_net
    except Exception:
        pass
    try:
        paper = ingest_auto(
            stack.papers,
            title or ref or "untitled",
            text=text or None,
            tags=tag_list or None,
            allow_network=allow_net and not bool(text),
        )
        try:
            from aos.kernel import AgentKernel

            root = os.getenv("ROBIN_USB_ROOT") or os.getenv("AOS_USB_ROOT")
            if root:
                k = AgentKernel.create(Path(root))
                k.soul.append(
                    "semantic",
                    f"Paper: {paper.title}\n{paper.summary}",
                    meta={"paper_id": paper.id, "source": paper.source, "tags": paper.tags},
                )
        except Exception:
            pass
        return _ok(
            {
                "ingested": paper.id,
                "title": paper.title,
                "claims": len(paper.claims),
                "promoted": paper.promoted,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _err(str(exc))


def paper_search(query: str, limit: int = 8) -> str:
    return _ok(_stack().retrieve_for(query, limit=int(limit)))


def paper_promote(paper_id: str, skill_hint: str = "") -> str:
    p = _stack().papers.promote(paper_id, skill_hint=skill_hint)
    if not p:
        return _err(f"paper not found: {paper_id}")
    return _ok({"promoted": p.id, "skill_hint": p.skill_hint})


def capability_rank(task: str = "reasoning") -> str:
    stack = _stack()
    ranked = stack.capabilities.rank(
        task,
        allow_cloud=True,
        prefer_uncensored=stack.prefer_uncensored,
        prefer_privacy=stack.prefer_privacy,
    )
    return _ok({"task": task, "ranked": [{"id": r.get("id"), "score": r.get("score")} for r in ranked]})


def curation_add_sft(prompt: str, completion: str) -> str:
    name = _stack().curation.add_sft(prompt=prompt, completion=completion)
    return _ok({"saved": name})


def curation_export(kind: str = "sft") -> str:
    path = _stack().curation.export_jsonl(kind=kind)
    return _ok({"export": str(path), "status": _stack().curation.status()})


def _seed():
    root = os.getenv("ROBIN_USB_ROOT") or os.getenv("AOS_USB_ROOT") or "."
    from robin_igris.lived_seed import LivedSeed

    return LivedSeed.create(Path(root))


def lived_status() -> str:
    return _ok(_seed().status())


def lived_ask(text: str) -> str:
    return _ok({"reply": _seed().ask(text)})


def lived_sleep(budget: int = 40) -> str:
    return _ok(_seed().sleep(budget=int(budget)))


def lived_teach(user_text: str, fact: str, outcome: str = "user_satisfied") -> str:
    """Explicit teaching episode — strengthens Hebbian links without OmniRoute."""
    seed = _seed()
    exp = seed.observe_turn(user_text, fact, outcome=outcome, source="teach")
    return _ok({"taught": exp.id, "concepts": exp.linked_concepts, "novelty": exp.novelty})


def _novel():
    root = Path(os.getenv("ROBIN_USB_ROOT") or os.getenv("AOS_USB_ROOT") or ".")
    from robin_igris.lived_seed import LivedSeed
    from robin_igris.novel_llm import NovelLLM

    seed = LivedSeed.create(root)
    papers = None
    soul = None
    try:
        from robin_igris.intelligence import IntelligenceStack

        stack = IntelligenceStack.create(root)
        papers = stack.papers
    except Exception:
        pass
    try:
        from aos.kernel import AgentKernel

        if os.getenv("ROBIN_USB_ROOT") or os.getenv("AOS_USB_ROOT"):
            soul = AgentKernel.create(root).soul
    except Exception:
        pass
    return NovelLLM.create(root, seed=seed, papers=papers, soul=soul)


def novel_status() -> str:
    return _ok(_novel().status())


def novel_forward(query: str) -> str:
    return _ok(_novel().forward(query))


TOOL_IMPLS: dict[str, Callable[..., str]] = {
    "intel_status": intel_status,
    "paper_ingest": paper_ingest,
    "paper_search": paper_search,
    "paper_promote": paper_promote,
    "capability_rank": capability_rank,
    "curation_add_sft": curation_add_sft,
    "curation_export": curation_export,
    "lived_status": lived_status,
    "lived_ask": lived_ask,
    "lived_sleep": lived_sleep,
    "lived_teach": lived_teach,
    "novel_status": novel_status,
    "novel_forward": novel_forward,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "intel_status",
            "description": "Show intelligence stack: model capabilities, papers, curation.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "paper_ingest",
            "description": "Ingest a paper or OSINT note into the agent library (text= offline; arxiv/url when network allowed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref": {"type": "string"},
                    "text": {"type": "string"},
                    "title": {"type": "string"},
                    "tags": {"type": "string", "description": "Comma-separated tags"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "paper_search",
            "description": "RAG search over papers + PAM soul memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 8},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "paper_promote",
            "description": "Mark a paper as promoting a Kairn skill after it improves capability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string"},
                    "skill_hint": {"type": "string"},
                },
                "required": ["paper_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capability_rank",
            "description": "Rank LLM routes for a task kind using the learned capability model.",
            "parameters": {
                "type": "object",
                "properties": {"task": {"type": "string", "default": "reasoning"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "curation_add_sft",
            "description": "Add a prompt/completion pair to the local fine-tune curation set.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "completion": {"type": "string"},
                },
                "required": ["prompt", "completion"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "curation_export",
            "description": "Export curated SFT or preference jsonl for idle NPU fine-tuning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "description": "sft|prefs", "default": "sft"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lived_status",
            "description": "Status of the blank Lived Seed (Hebbian/STDP experience learner).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lived_ask",
            "description": "Ask the Lived Seed only (no OmniRoute). Blank until it has lived enough.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lived_sleep",
            "description": "Run overnight consolidation: replay, prune, synthesize (not gradient descent).",
            "parameters": {
                "type": "object",
                "properties": {"budget": {"type": "integer", "default": 40}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lived_teach",
            "description": "Teach the Lived Seed a fact as a structured experience episode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_text": {"type": "string"},
                    "fact": {"type": "string"},
                    "outcome": {"type": "string", "default": "user_satisfied"},
                },
                "required": ["user_text", "fact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "novel_status",
            "description": "Status of the Novel LLM hybrid (not next-token architecture).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "novel_forward",
            "description": "Run one Novel LLM forward pass: memory-as-compute + world-model action + living weights.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]
