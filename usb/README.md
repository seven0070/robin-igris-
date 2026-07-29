# Robin Igris — 128GB USB Pendrive Kit

Plug the drive into **any PC**. Two modes:

| Mode | Entry | Meaning |
|------|-------|---------|
| **Companion** | `LAUNCH.bat` / `launch.sh` | App on stick, PC as display |
| **Agent OS** | `AOS_BOOT.bat` / `aos-boot.sh` | **Agent is the OS shell** — no desktop UX |

```
┌───────────── 128GB USB ─────────────┐     ┌────── Host PC ──────┐
│  AOS control plane (manifest/soul)  │     │  Borrowed display   │
│  Soul Merkle-DAG (identity+memory)  │────▶│  Borrowed mic/spk   │
│  Companion avatar = the shell       │     │  (discovered fresh) │
└─────────────────────────────────────┘     └─────────────────────┘
```

See [docs/research/PENDRIVE_AGENT_OS.md](../docs/research/PENDRIVE_AGENT_OS.md).

## Space budget (128GB)

| Slice | Size | Contents |
|-------|------|----------|
| App + companion + AOS | ~1–2 GB | Code, Live2D, control plane |
| Portable Python | ~1–2 GB | Runtime on the stick |
| Live ISO (optional) | ~2–4 GB | True boot-from-USB (Ventoy) |
| Soul + System 3 data | grows | Journal, Merkle DAG, skills |
| Free / models | **~100GB** | Local LLMs, media |

Format **exFAT** (Win/macOS/Linux) or **NTFS** (Windows-only).

## One-time prepare

```bash
./scripts/prepare-usb.sh /path/to/USB/ROBIN_IGRIS
# Windows: .\scripts\prepare-usb.ps1 E:\ROBIN_IGRIS
```

Edit `USB/ROBIN_IGRIS/.env` (API keys). Eject.

## Daily use

**Agent OS mode (recommended for the “OS on a stick” vision):**
1. Plug in USB
2. Ensure OmniRoute is available on the host (`npm i -g omniroute`) — LAUNCH starts it
3. Double-click **`AOS_BOOT.bat`** (Windows) or run **`./aos-boot.sh`**
4. Avatar / CLI shell talks through OmniRoute (`:20128`)
5. Ctrl+C or STOP → soul seals → eject (unplug = intentional shutdown)

**Companion mode:** `LAUNCH.bat` / `launch.sh` (starts OmniRoute + voice + Live2D).

LLM docs: [docs/OMNIROUTE.md](../docs/OMNIROUTE.md)

## Live USB (boot the PC from the stick)

See [scripts/build-liveusb-notes.md](../scripts/build-liveusb-notes.md) — Ventoy + Debian Live
auto-login into `aos-boot.sh` so there is no desktop, only the agent.

## Safety

- Prefer STOP/Ctrl+C before yanking (seals Merkle tip).
- Backup `data/aos/soul/` — that is the cryptographic identity.
- Modern Windows blocks autorun; always double-click the launcher.
