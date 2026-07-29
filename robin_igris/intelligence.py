"""Intelligence stack facade — capability routing + papers + RAG + curation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aos.research.papers import PaperRepository
from aos.research.rag import as_prompt as rag_prompt
from aos.research.rag import retrieve
from aos.soul import SoulStore
from robin_igris.model_capabilities import CapabilityModel
from robin_igris.system3.curation import CurationStore


@dataclass
class IntelligenceStack:
    """Layered intelligence: models + knowledge + reasoning + self-evolution data."""

    root: Path
    capabilities: CapabilityModel
    papers: PaperRepository
    curation: CurationStore
    soul: SoulStore | None = None
    prefer_uncensored: bool = True
    prefer_privacy: bool = False

    @classmethod
    def create(
        cls,
        usb_root: Path,
        *,
        soul: SoulStore | None = None,
        prefer_uncensored: bool = True,
        prefer_privacy: bool = False,
    ) -> "IntelligenceStack":
        usb_root = Path(usb_root)
        intel_root = usb_root / "data" / "aos" / "intelligence"
        research_root = usb_root / "data" / "aos" / "research"
        curation_root = usb_root / "data" / "system3" / "curation"
        return cls(
            root=intel_root,
            capabilities=CapabilityModel.load(intel_root),
            papers=PaperRepository(research_root),
            curation=CurationStore(curation_root),
            soul=soul,
            prefer_uncensored=prefer_uncensored,
            prefer_privacy=prefer_privacy,
        )

    def status(self) -> dict[str, Any]:
        return {
            "capabilities": self.capabilities.status(),
            "papers": self.papers.status(),
            "curation": self.curation.status(),
            "prefer_uncensored": self.prefer_uncensored,
            "prefer_privacy": self.prefer_privacy,
            "growth": {
                "axiom": "Domain+tools+memory beats generic FLOPs for *your* work",
                "phases": [
                    "route to best when online",
                    "grow PAM + paper graph past training cutoff",
                    "stack Kairn skills as reasoning modules",
                    "curate + fine-tune local model on your data",
                ],
            },
        }

    def retrieve_for(self, query: str, limit: int = 6) -> dict[str, Any]:
        return retrieve(query, papers=self.papers, soul=self.soul, limit=limit)

    def context_prompt(self, query: str | None = None) -> str:
        parts = [
            "## Intelligence stack\n"
            "Local model = uncensored + private. Cloud spillover = Manifest/WiFi gated.\n"
            "Papers/OSINT live in agent format; RAG + Kairn skills close the FLOPs gap.\n",
            self.capabilities.context_prompt(),
            self.papers.context_prompt(query),
        ]
        if query:
            parts.append(rag_prompt(self.retrieve_for(query)))
        parts.append(
            "## Curation / fine-tune\n"
            f"```json\n{json.dumps(self.curation.status(), indent=2)}\n```\n"
        )
        return "\n".join(parts)
