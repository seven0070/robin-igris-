# Optional fallback agent (no Hermes)

When OmniRoute / Hermes are unavailable, the lightweight tool agent still works
if any OpenAI-compatible endpoint is reachable (defaults to OmniRoute):

```bash
pip install -r requirements.txt
cp .env.example .env   # OmniRoute on :20128 by default
./scripts/start-omniroute.sh   # in another terminal
python main.py
```

Prefer OmniRoute + companion for the full Robin Igris experience (avatar + voice).
See [docs/OMNIROUTE.md](OMNIROUTE.md).
