"""Ingest papers / OSINT into the agent-native repository."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from aos.research.papers import PaperRecord, PaperRepository


_ARXIV_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/|arxiv:)(\d{4}\.\d{4,5})(v\d+)?", re.I)


def parse_arxiv_id(text: str) -> str | None:
    m = _ARXIV_RE.search(text or "")
    return m.group(1) if m else None


def ingest_local_file(repo: PaperRepository, path: Path, *, tags: list[str] | None = None) -> PaperRecord:
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    title = path.stem.replace("_", " ").replace("-", " ")
    # first markdown heading
    for line in text.splitlines()[:30]:
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return repo.ingest_text(
        title=title,
        text=text,
        source="local_file",
        url=str(path),
        tags=(tags or []) + ["osint" if "osint" in path.name.lower() else "paper"],
    )


def ingest_markdown(
    repo: PaperRepository,
    *,
    title: str,
    markdown: str,
    source: str = "osint",
    url: str = "",
    tags: list[str] | None = None,
) -> PaperRecord:
    return repo.ingest_text(
        title=title,
        text=markdown,
        source=source,
        url=url,
        tags=tags or [source],
    )


def fetch_arxiv_abs(arxiv_id: str) -> dict[str, Any]:
    """Fetch arXiv atom abstract (network). Raises on failure."""
    import httpx

    aid = arxiv_id.strip()
    url = f"http://export.arxiv.org/api/query?id_list={aid}"
    with httpx.Client(timeout=25.0, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        xml = r.text
    title = _xml_tag(xml, "title") or aid
    summary = _xml_tag(xml, "summary") or ""
    authors = re.findall(r"<name>([^<]+)</name>", xml)
    link = f"https://arxiv.org/abs/{aid}"
    return {
        "title": " ".join(title.split()),
        "abstract": " ".join(summary.split()),
        "authors": authors,
        "url": link,
        "body": f"# {_clean(title)}\n\n## Abstract\n\n{_clean(summary)}\n",
    }


def _xml_tag(xml: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}[^>]*>([\s\S]*?)</{tag}>", xml)
    return m.group(1).strip() if m else None


def _clean(s: str) -> str:
    return " ".join(s.split())


def ingest_arxiv(repo: PaperRepository, arxiv_id_or_url: str, *, tags: list[str] | None = None) -> PaperRecord:
    aid = parse_arxiv_id(arxiv_id_or_url) or arxiv_id_or_url.strip()
    data = fetch_arxiv_abs(aid)
    return repo.ingest_text(
        title=data["title"],
        text=data["body"],
        source="arxiv",
        url=data["url"],
        authors=list(data.get("authors") or []),
        tags=(tags or []) + ["arxiv", "paper"],
    )


def ingest_auto(
    repo: PaperRepository,
    ref: str,
    *,
    text: str | None = None,
    tags: list[str] | None = None,
    allow_network: bool = False,
) -> PaperRecord:
    """Ingest from path, arxiv id/url, or raw text."""
    ref = (ref or "").strip()
    if text:
        title = ref or "untitled note"
        source = "osint" if "http" not in title else "web"
        return ingest_markdown(repo, title=title, markdown=text, source=source, url=ref if ref.startswith("http") else "", tags=tags)

    path = Path(ref)
    if path.exists() and path.is_file():
        return ingest_local_file(repo, path, tags=tags)

    if parse_arxiv_id(ref) or re.fullmatch(r"\d{4}\.\d{4,5}", ref):
        if not allow_network:
            raise PermissionError("arxiv fetch requires network + Manifest allow")
        return ingest_arxiv(repo, ref, tags=tags)

    if ref.startswith("http") and allow_network:
        # Minimal HTML-less fetch: store URL + fetched text snippet via httpx
        import httpx

        with httpx.Client(timeout=25.0, follow_redirects=True) as client:
            r = client.get(ref)
            r.raise_for_status()
            body = r.text
        # strip tags coarsely
        plain = re.sub(r"<script[\s\S]*?</script>", " ", body, flags=re.I)
        plain = re.sub(r"<style[\s\S]*?</style>", " ", plain, flags=re.I)
        plain = re.sub(r"<[^>]+>", " ", plain)
        plain = re.sub(r"\s+", " ", plain).strip()
        host = urlparse(ref).netloc
        return repo.ingest_text(
            title=f"OSINT {host}",
            text=plain[:30_000],
            source="osint_web",
            url=ref,
            tags=(tags or []) + ["osint", "web"],
        )

    raise FileNotFoundError(f"Cannot ingest ref={ref!r} (provide text= for offline notes)")
