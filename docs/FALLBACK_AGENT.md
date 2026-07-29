# Optional fallback agent (no Hermes)

When Hermes gateway is unavailable, the original lightweight tool agent still works:

```bash
pip install -r requirements.txt
cp .env.example .env   # set OPENAI_API_KEY
python main.py
```

Prefer Hermes + companion for the full Robin Igris experience (avatar + voice).
