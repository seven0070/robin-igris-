# Robin Igris — 128GB USB Pendrive Kit

Plug the drive into **any PC**. The agent runs **from the USB**; the PC is only the **display + keyboard/mic**.

```
┌───────────── 128GB USB ─────────────┐     ┌────── Host PC ──────┐
│  runtime (Python)                   │     │  Monitor (browser)  │
│  app (Robin + System 3 + CADVP)     │────▶│  Speakers / Mic     │
│  data (memory, journal, skills)     │     │  (no install needed)│
│  companion-dist (Live2D UI)         │     └─────────────────────┘
└─────────────────────────────────────┘
```

## Space budget (128GB)

| Slice | Size | Contents |
|-------|------|----------|
| App + companion build | ~1–2 GB | Code, Live2D assets, Cubism |
| Portable Python + deps | ~1–2 GB | Runtime on the stick |
| Hermes (optional) | ~2–5 GB | Agent brain on stick (`data/home/.hermes`) |
| Working data | ~5–20 GB | Journal, skills, delivery bus, logs |
| Free / models / media | **rest (~100GB)** | Local models, VRM packs, backups |

Format the stick **exFAT** (works on Windows + macOS + Linux) or **NTFS** if Windows-only.

## One-time prepare (on a machine with internet)

1. Mount / plug the empty 128GB drive (example mount: `/Volumes/ROBIN` or `E:\`).
2. From this repo:

```bash
# Linux / macOS
./scripts/prepare-usb.sh /path/to/USB/ROBIN_IGRIS

# Windows (PowerShell, from repo)
.\scripts\prepare-usb.ps1 E:\ROBIN_IGRIS
```

3. Edit `USB/ROBIN_IGRIS/.env` — add API keys (`OPENAI_API_KEY` or Hermes provider keys).
4. Safely eject. Done.

## Every day (any PC)

1. Plug in the USB.
2. Double-click:
   - **Windows:** `LAUNCH.bat`
   - **macOS:** `LAUNCH.command` (right-click → Open the first time)
   - **Linux:** `./launch.sh`
3. Browser opens to `http://127.0.0.1:8787` — Live2D + chat + voice.
4. When finished: close the launcher window or run `STOP.bat` / `./stop.sh`, then eject.

Nothing permanent is installed on the host (except OS may cache browser data). All memory stays on the stick.

## Optional: Hermes brain on the stick

If `hermes` is available while preparing, the prepare script can install Hermes with `HOME` pointed at the USB so the whole brain lives on the drive:

```bash
export HOME="/path/to/USB/ROBIN_IGRIS/data/home"
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
# then configure API_SERVER_* as in the main README
```

Without Hermes, the stick still runs: companion UI + voice + System 3 + local fallback agent.

## Safety

- Do not yank the drive while LAUNCH is running.
- Keep a backup of `data/` (journal + CADVP inbox = your agent’s memory).
- Modern Windows blocks `autorun.inf`; always double-click `LAUNCH.bat`.
