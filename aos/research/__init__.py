"""aos.research — paper/OSINT repository + RAG."""

from aos.research.ingest import ingest_auto, ingest_local_file, ingest_markdown
from aos.research.papers import PaperRecord, PaperRepository
from aos.research.rag import as_prompt as rag_prompt
from aos.research.rag import retrieve

__all__ = [
    "PaperRecord",
    "PaperRepository",
    "ingest_auto",
    "ingest_local_file",
    "ingest_markdown",
    "retrieve",
    "rag_prompt",
]
