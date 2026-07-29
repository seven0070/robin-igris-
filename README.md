# Robin Igris

Hermes Agent brain + AIRI Live2D companion + **System 3** persistence
(OpenLife / Sophia / OpenSkill).

```
You ──voice/chat──▶ Companion (AIRI Live2D)
                         │
                         ▼
              System 3 (heartbeat, budget, journal, skills)
                         │
                         ▼
                 Hermes API (:8642)
```

| Layer | Source | Role |
|-------|--------|------|
| **System 3** | [OpenLife](https://www.alphaxiv.org/abs/2606.31046), [Sophia](https://www.alphaxiv.org/abs/2512.18202), [OpenSkill](https://www.alphaxiv.org/abs/2606.06741), [Channel Fracture / CADVP](https://www.alphaxiv.org/abs/2606.04896v2) | Persistence, skills, **delivery verification** |
| **Brain** | [Hermes Agent](https://github.com/NousResearch/hermes-agent) | Tools, memory, skills hub |
| **Body** | [Project AIRI](https://github.com/moeru-ai/airi) | Live2D avatar + voice presence |

See [docs/research/FOUNDATIONS.md](docs/research/FOUNDATIONS.md).

## Quick start

### 1. Hermes
```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
hermes model
hermes config set API_SERVER_ENABLED true
hermes config set API_SERVER_KEY robin-igris-dev
hermes config set API_SERVER_CORS_ORIGINS http://127.0.0.1:5173
cp character/SOUL.md ~/.hermes/SOUL.md
hermes gateway
```

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

## Layout
```
character/SOUL.md
companion/                 AIRI Live2D stage
robin_igris/system3/       OpenLife/Sophia/OpenSkill layer
robin_igris/voice_server.py
docs/research/FOUNDATIONS.md
```

## License
MIT — see [LICENSE](LICENSE). Cubism SDK is subject to Live2D’s license (fetched at build).
