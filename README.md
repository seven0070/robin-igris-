# Robin Igris

A lightweight tool-using AI agent with a CLI and Gradio chat UI.

## What it does

**Robin Igris** talks to any OpenAI-compatible API and can call tools when needed:

| Tool | Purpose |
|------|---------|
| `calculator` | Safe math evaluation |
| `web_search` | Live web lookup (DuckDuckGo) |
| `get_current_time` | Current UTC time |
| `remember_note` / `recall_notes` | Session scratchpad |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — set OPENAI_API_KEY (and optional BASE_URL / MODEL)
```

Works with OpenAI, Groq, OpenRouter, Ollama, and other OpenAI-compatible endpoints.

## Usage

**Interactive CLI**

```bash
python main.py
```

**One-shot**

```bash
python main.py -p "What is sqrt(144) + 8?"
```

**Web UI**

```bash
python -m robin_igris.app
```

Open http://localhost:7860

## Project layout

```
robin_igris/
  agent.py   # tool-calling loop
  tools.py   # built-in tools
  llm.py     # OpenAI-compatible client
  cli.py     # terminal chat
  app.py     # Gradio UI
main.py
```

## License

MIT — see [LICENSE](LICENSE).
