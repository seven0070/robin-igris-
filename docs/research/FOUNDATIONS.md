# Research foundations for Robin Igris

Robin Igris combines recent work on **persistent / open-world / delivery-reliable agents**
with OmniRoute (LLM), optional Hermes (tools), AIRI (body), and
**[Pendrive-Native Agent OS](PNAOS_PAPER.md)** (agent-as-OS composition).

| Paper | Core idea | What we take |
|-------|-----------|--------------|
| [OpenLife](https://www.alphaxiv.org/abs/2606.31046) `arXiv:2606.31046` | Open-world ALIFE: async processes, semantic memory, verbal policy, **budget metabolism**, heartbeat, SOUL rewrite | Heartbeat, budget, journal → POLICY/SOUL |
| [Sophia](https://www.alphaxiv.org/abs/2512.18202) `arXiv:2512.18202` | **System 3** meta-layer: narrative identity, self/user models, hybrid reward, intrinsic goals | Executive monitor, drives, Growth Journal |
| [OpenSkill](https://www.alphaxiv.org/abs/2606.06741) `arXiv:2606.06741` | Open-world **skill self-evolution** + self-built virtual verifiers | Skill bootstrap + virtual-task refine |
| [Channel Fracture](https://www.alphaxiv.org/abs/2606.04896v2) `arXiv:2606.04896` | Hermes cron `skip_memory=True` silently blocks memory writes (**channel fracture**); **CADVP** + Three-Gate | CC-0 channel probe, inverse verification, Channel A delivery bus |

## Mapping onto our stack

```
System 3 (robin_igris/system3/)
  ├── ExecutiveMonitor
  ├── Heartbeat / Metabolism / Journal
  ├── SkillBootstrap
  └── CADVP DeliveryBus     ← Channel A (direct store); VETO Channel C (cron memory)
         │
         ▼
Hermes Agent (brain)  — interactive OK; cron memory FRACTURED by design
         │
         ▼
AIRI companion stage  — Live2D + voice
```

## Channel Fracture rule (critical for Hermes)

Hermes scheduler hardcodes `skip_memory=True` so cron sessions do not get memory tools.
Writer-side “success” can lie. Robin Igris therefore:

1. **CC-0** — probe channels; veto cron-delegated memory injection
2. **Channel matching** — heartbeat persists via **Channel A** (filesystem delivery bus)
3. **Inverse verification** — read back from the receiver inbox before confirming
4. **Three-Gate** — L1 structure → L2 evidence/hash match → L3 quality score

```bash
python -m robin_igris.system3.cli cadvp-probe
python -m robin_igris.system3.cli deliver "remember: deploy Fridays only"
```

## Design constraints

1. Persistence is normative (budget).
2. Hybrid appraisal (not scalar reward only).
3. Skills are portable markdown artifacts.
4. Identity is editable text (`character/SOUL.md` + journal).
5. **Never trust scheduled writes without receiver-side confirmation.**

We do not claim artificial life — this is a constructive reliability platform.
