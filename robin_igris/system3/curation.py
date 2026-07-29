"""Fine-tune / VPO curation — agent curates its own training data from experience."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CurationStore:
    """Export SFT + preference pairs for idle local fine-tunes."""

    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "sft").mkdir(parents=True, exist_ok=True)
        (self.root / "prefs").mkdir(parents=True, exist_ok=True)

    def add_sft(self, *, prompt: str, completion: str, meta: dict[str, Any] | None = None) -> str:
        row = {
            "ts": time.time(),
            "prompt": prompt[:8000],
            "completion": completion[:8000],
            "meta": meta or {},
        }
        name = f"sft-{int(time.time() * 1000)}.json"
        (self.root / "sft" / name).write_text(json.dumps(row, indent=2), encoding="utf-8")
        return name

    def add_preference(
        self,
        *,
        prompt: str,
        chosen: str,
        rejected: str,
        meta: dict[str, Any] | None = None,
    ) -> str:
        row = {
            "ts": time.time(),
            "prompt": prompt[:8000],
            "chosen": chosen[:8000],
            "rejected": rejected[:8000],
            "meta": meta or {},
        }
        name = f"pref-{int(time.time() * 1000)}.json"
        (self.root / "prefs" / name).write_text(json.dumps(row, indent=2), encoding="utf-8")
        return name

    def export_jsonl(self, kind: str = "sft") -> Path:
        """Write consolidated jsonl for training jobs."""
        src = self.root / ("sft" if kind == "sft" else "prefs")
        out = self.root / f"export_{kind}.jsonl"
        lines = []
        for p in sorted(src.glob("*.json")):
            try:
                lines.append(json.dumps(json.loads(p.read_text(encoding="utf-8")), ensure_ascii=False))
            except Exception:
                continue
        out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return out

    def status(self) -> dict[str, Any]:
        return {
            "sft_examples": len(list((self.root / "sft").glob("*.json"))),
            "preference_pairs": len(list((self.root / "prefs").glob("*.json"))),
            "exports": [p.name for p in self.root.glob("export_*.jsonl")],
            "note": "Idle NPU fine-tune uses export_sft.jsonl / export_prefs.jsonl (pipeline external).",
        }
