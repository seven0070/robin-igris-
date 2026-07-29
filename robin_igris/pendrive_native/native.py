"""Robin — pendrive-native model (hardware-up).

Designed for the left column: NPU, 4–8 GB LPDDR, 128 GB eMMC, USB watts.
No transformer. No next-token prediction. No backprop. No training data.
Three layers: thin engine · PAM graph on eMMC · metabolic plasticity.

The name is **Robin**. Carry is the OS. Robin is the mind on the stick.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from robin_igris.pendrive_native.engine import ThinEngine
from robin_igris.pendrive_native.graph_store import GraphStore
from robin_igris.pendrive_native.metabolism import idle_tick, overnight


NAME = "Robin"

HARDWARE_PROFILE = {
    "engine_params_m": 50,
    "engine_ram_mb": 50,
    "engine_power_mw_idle": 50,
    "storage": "emmc_128gb_class",
    "ram": "lpddr4x_4_8gb",
    "npu_tops": 1,
    "power_w": [2.5, 15],
    "not": ["transformer", "next-token", "backprop", "pretraining"],
}


@dataclass
class Robin:
    """Pendrive-native mind — finds in the graph, learns by metabolism, unique to this stick."""

    root: Path
    store: GraphStore
    engine: ThinEngine
    enabled: bool = True
    born_at: float = 0.0

    @classmethod
    def create(cls, usb_root: Path, *, enabled: bool = True) -> "Robin":
        root = Path(usb_root) / "data" / "aos" / "robin"
        # migrate legacy path if present
        legacy = Path(usb_root) / "data" / "aos" / "pendrive_native"
        if legacy.exists() and not root.exists():
            root = legacy
        root.mkdir(parents=True, exist_ok=True)
        store = GraphStore(root / "pam_graph.sqlite")
        born = store.get_meta("born_at")
        if born is None:
            born = time.time()
            store.set_meta("born_at", born)
            store.set_meta("name", NAME)
            store.set_meta(
                "timeline",
                {"day0": f"{NAME} born — empty graph — I don't know yet"},
            )
            store.add_proposition(
                subject="this_agent",
                relation="named",
                obj=NAME.lower(),
                text=f"Agent name is {NAME}",
                kind="identity",
                confidence=1.0,
            )
        return cls(
            root=root,
            store=store,
            engine=ThinEngine(store),
            enabled=enabled,
            born_at=float(born),
        )

    def ask(self, text: str) -> dict[str, Any]:
        """Conversation-phase metabolism (~µW–mW class)."""
        result = self.engine.respond(text)
        age_days = (time.time() - self.born_at) / 86400.0
        return {
            "name": NAME,
            "architecture": "robin-v0",
            "reply": result.reply,
            "found": result.found,
            "path": result.path,
            "stored": result.stored,
            "phase": "conversation",
            "power_mw": 0.001,
            "age_days": round(age_days, 3),
            "counts": self.store.counts(),
            "hardware": HARDWARE_PROFILE,
        }

    def idle(self) -> dict[str, Any]:
        report = idle_tick(self.store)
        return {"name": NAME, **report.to_dict()}

    def consolidate(self) -> dict[str, Any]:
        report = overnight(self.store)
        with (self.root / "metabolism.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "name": NAME, **report.to_dict()}) + "\n")
        return {"name": NAME, **report.to_dict()}

    def status(self) -> dict[str, Any]:
        age_days = (time.time() - self.born_at) / 86400.0
        counts = self.store.counts()
        return {
            "name": NAME,
            "enabled": self.enabled,
            "architecture": "robin-v0",
            "layers": {
                "1_thin_engine": "memory traversal GNN-class — not transformer",
                "2_pam_graph": "SQLite+FTS5+typed edges on eMMC",
                "3_metabolism": "conversation / idle / overnight — not SGD",
            },
            "hardware": HARDWARE_PROFILE,
            "counts": counts,
            "age_days": round(age_days, 3),
            "born_at": self.born_at,
            "soul_rewrite": self.store.get_meta("soul_rewrite"),
            "blank": counts["propositions"] <= 1,  # identity name alone
            "unique": "graph + fused identity key ⇒ not a clonable weight file",
        }

    def context_prompt(self) -> str:
        return (
            f"## {NAME} — pendrive-native mind (hardware-up)\n"
            "Designed for NPU / LPDDR / eMMC / USB watts — not H100 clusters.\n"
            "Knowledge in the graph. Engine only navigates. Learning is metabolism.\n"
            f"```json\n{json.dumps(self.status(), indent=2, default=str)}\n```\n"
        )


# Back-compat alias
PendriveNativeModel = Robin
