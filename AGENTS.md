# AGENTS.md

## Cursor Cloud specific instructions

Robin Igris = a Hermes/OpenAI **brain** (`robin_igris`), an AIRI Live2D **companion**
frontend (`companion/`), a FastAPI **voice bridge** (`robin_igris.voice_server`), a
**System 3** persistence layer (`robin_igris.system3`), and a **Pendrive Agent OS**
(`aos`). Standard commands live in `README.md`; this section only records
non-obvious caveats.

### Services (run in dev)
- Voice bridge (FastAPI): `python3 -m robin_igris.voice_server` → `:8787`. `/health` and TTS work with no API key.
- Companion (Vite + Live2D): `npm --prefix companion run dev` → `:5173`.
- Gradio fallback agent: `python3 -m robin_igris.app` → `:7860`.
- System 3 CLI: `python3 -m robin_igris.system3.cli <status|deliver|credit|cadvp-probe|wake|heartbeat|skill>`.
- Pendrive Agent OS CLI: `python3 -m aos <status|probe|init|boot|...>`.

### Non-obvious caveats
- Python deps install to the user site (`~/.local`), not a venv. Always invoke
  code with `python3 -m ...` (the `python` alias does not exist; only `python3`).
- `pytest` is required for the test suite but is **not** in `requirements.txt`; the
  update script installs it separately. Run tests with `python3 -m pytest`.
- Conversational chat (the agent loop) needs either `OPENAI_API_KEY` (used by the
  Gradio fallback agent and `Agent`) or a running **Hermes gateway** on `:8642`.
  Hermes is an external binary that is **not installed** in this environment. With
  neither present, the companion shows "Hermes offline", Gradio chat returns an
  `OPENAI_API_KEY is not set` error, and System 3 `wake`/`heartbeat` fall back to
  an error string — everything else (avatar render, voice TTS, delivery, budget,
  journal, AOS) works. Set `OPENAI_API_KEY` in `.env` to enable chat.
- Default TTS provider is `edge` (edge-tts), which needs network egress to
  Microsoft — no API key required. `/v1/audio/speech` returns real MP3 audio.
- `companion` `npm run dev`/`build` runs a `predev`/`prebuild` hook plus Vite
  plugins that **download a Live2D model + the Cubism SDK from the network** on
  first run (into `companion/public/assets/…`). Needs egress the first time; cached
  after that. `npm install` alone does not trigger the download.
- System 3 `deliver` CLI exits with code **2** (not 0) when a delivery is *not*
  confirmed. This is by design: the CADVP L3 quality gate needs content ≥40 chars
  with a `kind` to score ≥0.9. Short payloads legitimately fail — not a bug.
- No linter is configured (no ruff/flake8/eslint/pyproject and no lint npm script).
  `vue-tsc` is not part of the build (`vite build` uses esbuild) and reports
  pre-existing type errors only in `vite.config.ts`; do not treat it as a gate.
