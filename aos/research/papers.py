"""Paper / OSINT repository in agent-native (PAM-linked) format."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (s[:48] or "paper") + "-" + hashlib.sha256(text.encode()).hexdigest()[:8]


def _extract_claims(text: str, limit: int = 12) -> list[dict[str, str]]:
    """Heuristic claim/method/result extraction — no LLM required."""
    claims: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if len(line) < 40:
            continue
        low = line.lower()
        kind = "claim"
        if any(k in low for k in ("we propose", "method", "algorithm", "approach")):
            kind = "method"
        elif any(k in low for k in ("result", "achieve", "outperform", "accuracy", "score")):
            kind = "result"
        elif not any(k in low for k in ("show that", "find that", "argue", "claim", "conclude")):
            if not line.endswith(".") or len(line) > 280:
                continue
        claims.append({"text": line[:500], "kind": kind})
        if len(claims) >= limit:
            break
    if not claims and text.strip():
        # fallback: first non-empty paragraphs
        for para in re.split(r"\n\s*\n", text.strip())[:5]:
            p = " ".join(para.split())
            if len(p) > 40:
                claims.append({"text": p[:500], "kind": "claim"})
    return claims


@dataclass
class PaperRecord:
    id: str
    title: str
    source: str
    url: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    body: str = ""
    claims: list[dict[str, str]] = field(default_factory=list)
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    promoted: bool = False
    skill_hint: str = ""
    ingested_at: float = field(default_factory=time.time)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "authors": self.authors,
            "abstract": self.abstract,
            "body": self.body[:50_000],
            "claims": self.claims,
            "summary": self.summary,
            "tags": self.tags,
            "links": self.links,
            "promoted": self.promoted,
            "skill_hint": self.skill_hint,
            "ingested_at": self.ingested_at,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaperRecord":
        return cls(
            id=str(data.get("id") or uuid.uuid4()),
            title=str(data.get("title") or "untitled"),
            source=str(data.get("source") or "local"),
            url=str(data.get("url") or ""),
            authors=list(data.get("authors") or []),
            abstract=str(data.get("abstract") or ""),
            body=str(data.get("body") or ""),
            claims=list(data.get("claims") or []),
            summary=str(data.get("summary") or ""),
            tags=list(data.get("tags") or []),
            links=list(data.get("links") or []),
            promoted=bool(data.get("promoted")),
            skill_hint=str(data.get("skill_hint") or ""),
            ingested_at=float(data.get("ingested_at") or time.time()),
            meta=dict(data.get("meta") or {}),
        )


@dataclass
class PaperRepository:
    """Durable paper store under data/aos/research/papers."""

    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        (self.root / "papers").mkdir(parents=True, exist_ok=True)
        (self.root / "index").mkdir(parents=True, exist_ok=True)

    def _path(self, paper_id: str) -> Path:
        return self.root / "papers" / f"{paper_id}.json"

    def save(self, paper: PaperRecord) -> PaperRecord:
        path = self._path(paper.id)
        path.write_text(json.dumps(paper.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        self._reindex()
        return paper

    def get(self, paper_id: str) -> PaperRecord | None:
        path = self._path(paper_id)
        if not path.exists():
            return None
        return PaperRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_papers(self, limit: int = 100) -> list[dict[str, Any]]:
        files = sorted((self.root / "papers").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        out: list[dict[str, Any]] = []
        for p in files[:limit]:
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                out.append(
                    {
                        "id": d.get("id"),
                        "title": d.get("title"),
                        "source": d.get("source"),
                        "tags": d.get("tags"),
                        "promoted": d.get("promoted"),
                        "claims": len(d.get("claims") or []),
                    }
                )
            except Exception:
                continue
        return out

    def ingest_text(
        self,
        *,
        title: str,
        text: str,
        source: str = "local",
        url: str = "",
        authors: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> PaperRecord:
        abstract = ""
        body = text.strip()
        # If markdown with Abstract section
        m = re.search(r"(?i)^#+\s*abstract\s*$([\s\S]+?)(?=^#|\Z)", body, re.M)
        if m:
            abstract = m.group(1).strip()[:2000]
        elif len(body) > 400:
            abstract = body[:600]
        claims = _extract_claims(body)
        summary = abstract or (claims[0]["text"] if claims else title)
        paper = PaperRecord(
            id=_slug(title + url),
            title=title.strip() or "untitled",
            source=source,
            url=url,
            authors=authors or [],
            abstract=abstract,
            body=body,
            claims=claims,
            summary=summary[:1500],
            tags=tags or [],
            skill_hint=f"summarize_and_apply:{title[:60]}",
        )
        return self.save(paper)

    def promote(self, paper_id: str, skill_hint: str = "") -> PaperRecord | None:
        paper = self.get(paper_id)
        if not paper:
            return None
        paper.promoted = True
        if skill_hint:
            paper.skill_hint = skill_hint
        return self.save(paper)

    def link(self, a_id: str, b_id: str) -> None:
        for src, dst in ((a_id, b_id), (b_id, a_id)):
            p = self.get(src)
            if p and dst not in p.links:
                p.links.append(dst)
                self.save(p)

    def _reindex(self) -> None:
        docs = []
        for path in (self.root / "papers").glob("*.json"):
            try:
                d = json.loads(path.read_text(encoding="utf-8"))
                blob = " ".join(
                    [
                        str(d.get("title") or ""),
                        str(d.get("abstract") or ""),
                        str(d.get("summary") or ""),
                        " ".join(d.get("tags") or []),
                        " ".join(c.get("text", "") for c in (d.get("claims") or [])),
                    ]
                ).lower()
                docs.append({"id": d.get("id"), "title": d.get("title"), "text": blob})
            except Exception:
                continue
        (self.root / "index" / "inverted.json").write_text(
            json.dumps({"docs": docs, "updated": time.time()}, indent=2),
            encoding="utf-8",
        )

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        idx_path = self.root / "index" / "inverted.json"
        if not idx_path.exists():
            self._reindex()
        data = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {"docs": []}
        tokens = [t for t in re.findall(r"[a-z0-9]{3,}", query.lower())]
        if not tokens:
            return []
        scored = []
        for doc in data.get("docs") or []:
            text = doc.get("text") or ""
            score = sum(text.count(t) for t in tokens)
            if score > 0:
                scored.append({"id": doc.get("id"), "title": doc.get("title"), "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def status(self) -> dict[str, Any]:
        papers = self.list_papers(limit=10_000)
        return {
            "count": len(papers),
            "promoted": sum(1 for p in papers if p.get("promoted")),
            "recent": papers[:10],
        }

    def context_prompt(self, query: str | None = None, limit: int = 5) -> str:
        if query:
            hits = self.search(query, limit=limit)
            details = []
            for h in hits:
                p = self.get(str(h["id"]))
                if p:
                    details.append(
                        {
                            "id": p.id,
                            "title": p.title,
                            "summary": p.summary[:400],
                            "claims": p.claims[:3],
                            "promoted": p.promoted,
                        }
                    )
            payload = {"query": query, "hits": details}
        else:
            payload = self.status()
        return (
            "## Paper / OSINT repository (PAM-linked)\n"
            "Knowledge grows by ingesting papers; only promote what improves skills.\n"
            f"```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```\n"
        )
