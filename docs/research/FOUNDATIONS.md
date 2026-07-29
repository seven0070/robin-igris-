# Research foundations for Robin Igris

Robin Igris combines three recent lines of work on **persistent / open-world agents** with Hermes (brain) and AIRI (body).

| Paper | Core idea | What we take |
|-------|-----------|--------------|
| [OpenLife](https://www.alphaxiv.org/abs/2606.31046) `arXiv:2606.31046` | Open-world ALIFE: society of async processes, semantic memory graph, verbal policy, **budget metabolism**, spontaneous heartbeat, SOUL self-rewrite | Heartbeat, budget, journal → POLICY/SOUL, spontaneous intrinsic wakes |
| [Sophia](https://www.alphaxiv.org/abs/2512.18202) `arXiv:2512.18202` | **System 3** meta-layer: narrative identity, self/user models, hybrid reward, process-supervised thought search, intrinsic goals | Executive monitor, intrinsic drives, self-model, episodic Growth Journal |
| [OpenSkill](https://www.alphaxiv.org/abs/2606.06741) `arXiv:2606.06741` | Open-world **skill self-evolution**: acquire docs/repos/web → skills; refine vs **self-built virtual verifiers** (no target-task leakage) | Skill bootstrap pipeline + virtual-task refine loop |

## Mapping onto our stack

```
System 3 (this repo: robin_igris/system3/)
  ├── ExecutiveMonitor   — Sophia-style goal / reward / reflection
  ├── Heartbeat          — OpenLife spontaneous wake
  ├── Metabolism         — budget = operational life
  ├── Journal            — narrative + POLICY distillate
  └── SkillBootstrap     — OpenSkill-style acquire → virtual verify → skill.md
         │
         ▼
Hermes Agent (brain)  ←── tools, memory, skills hub, API :8642
         │
         ▼
AIRI companion stage  ←── Live2D + voice (body)
```

## Design constraints we keep

1. **Persistence is normative** — budget exhaustion is “death”; spontaneous work must earn its keep (OpenLife).
2. **No fixed scalar reward only** — hybrid extrinsic + intrinsic natural-language appraisal (Sophia / OpenLife VPO).
3. **Skills are portable artifacts** — markdown skills refined against virtual tests, not weight updates (OpenSkill).
4. **Identity is editable text** — `character/SOUL.md` + runtime journal; the next wake reconstructs self from files (OpenLife).

## What we are *not* claiming

We do not claim artificial life or full autonomy. Like the papers, this is a constructive platform: Hermes supplies capable automation; System 3 aims at **self-directed continuity**.
