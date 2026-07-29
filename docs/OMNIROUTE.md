# OmniRoute LLM gateway

Robin Igris uses **[OmniRoute](https://github.com/diegosouzapw/OmniRoute)** as the
primary LLM brain — one local OpenAI-compatible endpoint with auto-fallback across
290+ providers (90+ free).

```
You / Companion / AOS / System3
        │
        ▼
  OmniRoute :20128/v1   (model=auto)
        │
        ▼
  free / cheap / API / subscription providers
```

## Install & run

```bash
# Option A — npm global
npm i -g omniroute
omniroute

# Option B — helper script
./scripts/start-omniroute.sh

# Option C — Docker
docker run -d --name omniroute -p 127.0.0.1:20128:20128 \
  -v omniroute-data:/app/data diegosouzapw/omniroute:latest
```

Dashboard: http://127.0.0.1:20128  
API: http://127.0.0.1:20128/v1  

Create an API key in the OmniRoute dashboard (API Manager) and put it in `.env`
as `OMNIROUTE_API_KEY` / `OPENAI_API_KEY`. Fresh installs often answer with
keyless free providers using model `auto`.

## Robin env

```env
OMNIROUTE_BASE_URL=http://127.0.0.1:20128/v1
OMNIROUTE_API_KEY=omniroute
OMNIROUTE_MODEL=auto
OPENAI_BASE_URL=http://127.0.0.1:20128/v1
OPENAI_API_KEY=omniroute
OPENAI_MODEL=auto
ROBIN_START_OMNIROUTE=1
```

USB `LAUNCH` / `portable_boot` will start OmniRoute when `omniroute` or `npx` is available.

## Check

```bash
curl -s http://127.0.0.1:20128/v1/models -H "Authorization: Bearer omniroute" | head
python -c "from robin_igris.omniroute import health, chat_text; print(health()); print(chat_text([{'role':'user','content':'hi'}])[:200])"
```
