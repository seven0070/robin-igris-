"""Novel LLM hybrid — five directions that are not next-token prediction.

Directions unified:
  1. Memory-as-Compute — knowledge in PAM/graph, tiny reasoning core
  2. Living Weights — Hebbian/STDP on every forward pass
  3. Program-Synthesis — write/execute/verify Kairn-like skills
  4. Predictive World Model — choose actions by simulated outcomes
  5. Overnight consolidation — sleep replay (Lived Seed)

OmniRoute remains dual-track for capability *now*; this stack becomes you-shaped.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from robin_igris.lived_seed.seed import LivedSeed
from robin_igris.novel_llm.memory_compute import reason_over_memories, retrieve_working_set
from robin_igris.novel_llm.program_synth import SkillLibrary, run_program_synthesis
from robin_igris.novel_llm.simulator import as_dict, choose_action, simulate_futures


@dataclass
class NovelLLM:
    """A different way entirely — not a variant of transformer next-token training."""

    root: Path
    seed: LivedSeed
    skills: SkillLibrary
    papers: Any | None = None
    soul: Any | None = None
    enabled: bool = True

    @classmethod
    def create(
        cls,
        usb_root: Path,
        *,
        seed: LivedSeed | None = None,
        papers: Any | None = None,
        soul: Any | None = None,
        enabled: bool = True,
    ) -> "NovelLLM":
        usb_root = Path(usb_root)
        root = usb_root / "data" / "aos" / "novel_llm"
        root.mkdir(parents=True, exist_ok=True)
        lived = seed or LivedSeed.create(usb_root)
        return cls(
            root=root,
            seed=lived,
            skills=SkillLibrary(root / "skills"),
            papers=papers,
            soul=soul,
            enabled=enabled,
        )

    def forward(self, query: str) -> dict[str, Any]:
        """One forward pass — NOT next-token prediction.

        Pipeline:
          retrieve memories → simulate futures → act (memory / synth / defer)
          → living weight update → optional memory writeback note
        """
        t0 = time.time()
        memories = retrieve_working_set(
            query,
            graph=self.seed.graph,
            papers=self.papers,
            soul=self.soul,
            limit=8,
        )
        # Living weights: activations already applied in retrieve_working_set via graph.fire
        self.seed.graph.save()

        sims = simulate_futures(query, graph=self.seed.graph, world=self.seed.world)
        action = choose_action(sims)

        memory_text = reason_over_memories(query, memories)
        snippets = [m.content for m in memories if m.content]

        branch: dict[str, Any]
        if action.name == "synthesize_skill":
            branch = run_program_synthesis(query, library=self.skills, memory_snippets=snippets)
            reply = branch["reply"]
        elif action.name == "answer_from_memory":
            branch = {"mode": "memory_as_compute"}
            reply = memory_text
        elif action.name == "ask_clarifying_question":
            branch = {"mode": "clarify"}
            hints = [", ".join(m.content.split()[:3]) for m in memories[:3]]
            hint_txt = "; ".join(h for h in hints if h) or "more context"
            reply = (
                "[novel/world-model] Simulation preferred clarifying question. "
                f"Which of these matter: {hint_txt}?"
            )
        elif action.name == "say_nothing":
            branch = {"mode": "silence"}
            reply = "[novel/world-model] Simulation: saying nothing has higher value — waiting."
        else:
            branch = {"mode": "defer_omniroute"}
            reply = (
                "[novel/hybrid] World-model chose defer_to_omniroute for capability now. "
                "Lived weights still update when OmniRoute answers; I remain blank-pretrained."
            )

        # Record internal decision as a low-salience experience of the novel path itself
        self.seed.observe_turn(
            query,
            reply,
            outcome="unclear",
            salience=0.4,
            source=f"novel:{action.name}",
        )

        result = {
            "architecture": "novel-hybrid-v0",
            "not": "next-token-transformer",
            "directions": [
                "memory-as-compute",
                "living-weights",
                "program-synthesis",
                "predictive-world-model",
                "overnight-consolidation",
            ],
            "action": action.name,
            "simulations": as_dict(sims),
            "memories": [
                {"kind": m.kind, "score": m.score, "content": m.content[:200]} for m in memories
            ],
            "branch": branch,
            "reply": reply,
            "elapsed_s": round(time.time() - t0, 4),
            "graph": {
                "nodes": len(self.seed.graph.nodes),
                "edges": len(self.seed.graph.edges),
            },
        }
        self._audit(result)
        return result

    def sleep(self, budget: int = 40) -> dict[str, Any]:
        return self.seed.sleep(budget=budget)

    def _audit(self, result: dict[str, Any]) -> None:
        path = self.root / "forward.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "action": result.get("action"), "reply": result.get("reply", "")[:200]}) + "\n")

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "architecture": "novel-hybrid-v0",
            "directions": {
                "memory_as_compute": "knowledge in PAM/graph; weights only 'how to think'",
                "living_weights": "Hebbian/STDP every forward pass",
                "program_synthesis": "write/execute/verify Kairn-like skills",
                "predictive_world_model": "choose actions by simulated outcomes",
                "overnight_consolidation": "sleep replay — no gradient descent",
            },
            "lived_seed": self.seed.status(),
            "verified_skills": len(self.skills.list_verified()),
            "fits_pendrive": True,
            "uncensored": "inherent — no provider policy layer",
        }

    def context_prompt(self) -> str:
        return (
            "## Novel LLM (hybrid — not next-token training)\n"
            "Five directions: Memory-as-Compute · Living Weights · Program-Synthesis · "
            "World Model · Sleep consolidation. OmniRoute = dual-track capability now.\n"
            f"```json\n{json.dumps(self.status(), indent=2, default=str)}\n```\n"
        )
