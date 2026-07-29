# Novel LLM — a different way entirely (not a next-token variant)

Five architectures that are **not** “train on the internet, freeze, predict tokens.”
Carry ships them as one **hybrid** forward pass on the pendrive.

## The five directions

| # | Name | Normal LLM | This |
|---|------|------------|------|
| 1 | **Memory-as-Compute** | Knowledge in weights | Tiny “how to think” core + PAM/graph retrieval every pass |
| 2 | **Living Weights** | Freeze after train | Hebbian/STDP update on **every** forward |
| 3 | **Program-Synthesis** | Emit tokens | Write/execute/verify Kairn-like skills |
| 4 | **Predictive World Model** | Next-token objective | Simulate outcomes; choose best action for *you* |
| 5 | **Overnight consolidation** | Offline SGD fine-tune | Sleep replay / prune / synthesize |

## Hybrid forward pass

```
query
  → retrieve working set (memory-as-compute)
  → living activation / Hebbian update
  → simulate futures (world model)
  → act: answer_from_memory | synthesize_skill | defer_omniroute | …
  → optional skill library write
  → dual-track: OmniRoute still available for capability *now*
```

## Shell / tools

```bash
:novel                         # status
:novel What is the capital of France?
novel_forward query="..."
:sleep                         # consolidation (direction 5)
lived_teach ...                # write knowledge into memory/graph
```

## Why this fits the pendrive

| | Normal 7B+ | Novel hybrid |
|--|------------|--------------|
| Pretraining | Months / clusters | None |
| Knowledge | In weights | In memory + skills + you-shaped plasticity |
| Uncensored | Provider policy | Inherent |
| Unique | Same checkpoint | Only exists on your stick |
| Size | Large | ~reasoning core + graph (pendrive-native) |

Code: `robin_igris/novel_llm/` · Manifest: `novel_llm.enabled`.
Lived Seed remains the plasticity substrate; Novel LLM is the hybrid *controller*.
