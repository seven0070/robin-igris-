# Robin Igris

Hermes Agent tools (optional) + AIRI Live2D companion + **System 3** persistence
+ **[OmniRoute](https://github.com/diegosouzapw/OmniRoute)** as the LLM gateway
+ Pendrive-Native Agent OS.

```
You ──voice/chat──▶ Companion (AIRI Live2D)
                         │
                         ▼
              System 3 / AOS (soul, heartbeat, skills)
                         │
                         ▼
              OmniRoute :20128/v1  (model=auto)
                         │
              free / cheap / API providers
```

| Layer | Source | Role |
|-------|--------|------|
| **LLM** | [OmniRoute](https://github.com/diegosouzapw/OmniRoute) | Offline-first router: local 3–7B + cloud spillover |
| **Workspace** | [Buzz](https://buzz.xyz) ([block/buzz](https://github.com/block/buzz)) | Shared human+agent rooms, tasks, artifacts |
| **System 3** | [OpenLife](https://www.alphaxiv.org/abs/2606.31046), [Sophia](https://www.alphaxiv.org/abs/2512.18202), [OpenSkill](https://www.alphaxiv.org/abs/2606.06741), [Channel Fracture / CADVP](https://www.alphaxiv.org/abs/2606.04896v2) | Persistence, skills, **delivery verification** |
| **Tools (opt.)** | [Hermes Agent](https://github.com/NousResearch/hermes-agent) | Optional tools/memory hub |
| **Body** | [Project AIRI](https://github.com/moeru-ai/airi) | Live2D avatar + voice presence |
| **OS** | PNAOS (`aos/`) | Pendrive Agent OS — agent is the shell |

See [docs/research/FOUNDATIONS.md](docs/research/FOUNDATIONS.md), [docs/OMNIROUTE.md](docs/OMNIROUTE.md),
and [docs/BUZZ.md](docs/BUZZ.md).

## Quick start

### 1. OmniRoute (LLM)
```bash
npm i -g omniroute && omniroute
# or: ./scripts/start-omniroute.sh
cp .env.example .env   # OMNIROUTE_* / OPENAI_* already point at :20128
```

Dashboard: http://127.0.0.1:20128 — create an API key if prompted, set `OMNIROUTE_API_KEY`.

### 2. Voice + companion
```bash
pip install -r requirements.txt
python -m robin_igris.voice_server
cd companion && npm install && npm run dev
```

### 3. System 3
```bash
python -m robin_igris.system3.cli status
python -m robin_igris.system3.cli wake "Summarize this repo in 5 bullets"
python -m robin_igris.system3.cli heartbeat
python -m robin_igris.system3.cli skill "Write a safe git commit workflow"
python -m robin_igris.system3.cli credit 1.0   # basic income
python -m robin_igris.system3.cli cadvp-probe # Channel Fracture CC-0
python -m robin_igris.system3.cli deliver "fact: deploys happen on Fridays"
```

### Optional: Hermes tools hub
```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
# set ROBIN_START_HERMES=1 in .env if you want portable_boot to launch it
```

## Layout
```
character/SOUL.md
companion/                 AIRI Live2D stage
aos/                       Pendrive-Native Agent OS (manifest/soul/octopus)
robin_igris/system3/       OpenLife/Sophia/OpenSkill layer
robin_igris/voice_server.py
docs/research/FOUNDATIONS.md
docs/research/PENDRIVE_AGENT_OS.md
usb/                       Pendrive launchers (LAUNCH + AOS_BOOT)
```

## USB pendrive (128GB) — Agent OS

The stick is home; the PC is borrowed hardware; **the agent is the shell**.

```bash
./scripts/prepare-usb.sh /path/to/USB/ROBIN_IGRIS
# then: AOS_BOOT.bat  or  ./aos-boot.sh
```

Design paper: [docs/research/PENDRIVE_AGENT_OS.md](docs/research/PENDRIVE_AGENT_OS.md)  
Research write-up: [docs/research/PNAOS_PAPER.md](docs/research/PNAOS_PAPER.md)  
Vision (born for USB): [docs/research/PNAOS_VISION.md](docs/research/PNAOS_VISION.md)  
Kit guide: [usb/README.md](usb/README.md)

## License
MIT — see [LICENSE](LICENSE). Cubism SDK is subject to Live2D’s license (fetched at build).
