# Robin Igris

Hermes Agent brain + AIRI-style Live2D companion (voice + avatar).

```
You  ──voice/chat──▶  Companion Stage (AIRI Live2D + lipsync)
                           │
                           ▼
                    Hermes API (:8642)   ← tools, memory, skills (prebuilt)
```

| Layer | Source | Role |
|-------|--------|------|
| **Brain** | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | Tool-calling agent, memory, skills, TTS providers |
| **Body** | [moeru-ai/airi](https://github.com/moeru-ai/airi) | Live2D avatar (Hiyori presets), Cubism SDK, lipsync |
| **Glue** | this repo | Companion UI, voice bridge, Robin Igris character |

## Quick start

### 1. Install Hermes (the brain)

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc
hermes model          # pick a provider
hermes config set API_SERVER_ENABLED true
hermes config set API_SERVER_KEY robin-igris-dev
hermes config set API_SERVER_CORS_ORIGINS http://127.0.0.1:5173,http://localhost:5173
# optional: load character
cp character/SOUL.md ~/.hermes/SOUL.md
hermes gateway        # API on http://127.0.0.1:8642
```

### 2. Companion stage (avatar + voice)

```bash
cd companion
npm install
npm run dev           # http://127.0.0.1:5173
```

Allow mic access. Hold **Talk**, or type in the chat box. The Live2D model (AIRI’s Hiyori Free, from `dist.ayaka.moe`) lip-syncs to TTS.

### 3. Optional voice bridge

If you want server-side TTS (Edge / OpenAI) without Hermes Tool Gateway:

```bash
pip install -r requirements.txt
python -m robin_igris.voice_server
```

## Env

Copy `.env.example` → `.env` (companion reads Vite `VITE_*`; voice server reads the rest).

| Variable | Purpose |
|----------|---------|
| `VITE_HERMES_BASE_URL` | Hermes API, default `http://127.0.0.1:8642/v1` |
| `VITE_HERMES_API_KEY` | Must match `API_SERVER_KEY` |
| `VITE_VOICE_BASE_URL` | Voice bridge, default `http://127.0.0.1:8787` |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | Fallback TTS / chat if Hermes is down |

## Layout

```
character/SOUL.md     Robin Igris identity for Hermes
companion/            Vite + Vue Live2D stage (AIRI assets/plugins)
robin_igris/          Voice bridge + thin Hermes client helpers
scripts/setup.sh      Dependency checks
```

## Credits

- Agent runtime: [Hermes Agent](https://github.com/NousResearch/hermes-agent) (MIT) by Nous Research
- Avatar / Live2D tooling: [Project AIRI](https://github.com/moeru-ai/airi) (MIT) by Moeru AI — models via [`@proj-airi/unplugin-fetch`](https://www.npmjs.com/package/@proj-airi/unplugin-fetch) & [`@proj-airi/unplugin-live2d-sdk`](https://www.npmjs.com/package/@proj-airi/unplugin-live2d-sdk)

## License

MIT — see [LICENSE](LICENSE). Live2D Cubism SDK is subject to Live2D’s proprietary license (fetched at build time, same as AIRI).
