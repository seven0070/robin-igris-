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


TOOL_IMPLS: dict[str, Callable[..., str]] = {
    "intel_status": intel_status,
    "paper_ingest": paper_ingest,
    "paper_search": paper_search,
    "paper_promote": paper_promote,
    "capability_rank": capability_rank,
    "curation_add_sft": curation_add_sft,
    "curation_export": curation_export,
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
]
