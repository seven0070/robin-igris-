# Companion stage

AIRI-style Live2D avatar + voice UI for Robin Igris.

- Live2D model: **Hiyori Free** from Project AIRI’s CDN (`dist.ayaka.moe`)
- Cubism SDK: `@proj-airi/unplugin-live2d-sdk`
- Brain: Hermes Agent API (`/v1/chat/completions`)
- Mouth: Edge/OpenAI TTS via `robin_igris.voice_server` + amplitude lip-sync

```bash
npm install
npm run dev
```

Requires Hermes gateway (`API_SERVER_ENABLED=true`) and the voice bridge on `:8787`.
