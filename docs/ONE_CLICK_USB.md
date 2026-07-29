# One-click install → pendrive

Install **Robin Igris / Carry** onto a USB stick with a single double-click.

## Requirements

| | |
|--|--|
| Stick | USB drive, **exFAT** preferred (Win + Mac + Linux). NTFS OK on Windows. |
| Host | **Python 3.10+** and **Node.js / npm** (companion build) |
| Space | ~2 GB+ free on the stick (app + venv; more if you add models later) |
| This repo | Cloned or unzipped on the computer (not on the empty stick) |

## Steps

1. Plug the pendrive in.
2. Open the **Robin Igris repo** folder on your hard drive.
3. Run the installer:

| OS | Action |
|----|--------|
| **Windows** | Double-click **`INSTALL_TO_USB.bat`** |
| **macOS** | Double-click **`INSTALL_TO_USB.command`** (or `./INSTALL_TO_USB.sh` in Terminal) |
| **Linux** | `./INSTALL_TO_USB.sh` |

4. Confirm the detected USB path (or type a path if auto-detect fails).
5. Wait for copy + companion build + `venv` creation.
6. On the stick, open **`ROBIN_IGRIS/`**, edit **`.env`**, then run **`AOS_BOOT.bat`** / **`aos-boot.sh`**.

## What gets installed

```
<USB>/ROBIN_IGRIS/
  START_HERE.txt
  AOS_BOOT.bat / aos-boot.sh
  LAUNCH.bat / launch.sh / STOP.bat
  .env
  app/                 # repo copy
  runtime/venv/        # portable Python
  companion-dist/      # Live2D build
  data/aos/soul/       # identity (backup this)
  data/…               # shell, queue, system3, …
  bin/                   # helpers
  docs/ONE_CLICK_USB.md
```

## Override destination

```bash
# Unix — skip auto-detect
ROBIN_USB_DEST=/media/me/MYSTICK ./INSTALL_TO_USB.sh

# Or pass the kit folder directly to prepare
./scripts/prepare-usb.sh /media/me/MYSTICK/ROBIN_IGRIS
```

```powershell
# Windows
$env:ROBIN_USB_DEST = "E:\"
.\INSTALL_TO_USB.bat
# Or:
.\scripts\prepare-usb.ps1 -Dest E:\ROBIN_IGRIS
```

## After install

| Goal | On the stick |
|------|----------------|
| Boot Carry / Agent OS | `AOS_BOOT.bat` / `./aos-boot.sh` |
| Companion UI | `LAUNCH.bat` / `./launch.sh` |
| Pendrive mind | `:robin` in the shell |
| Unplug safely | Ctrl+C / `STOP.bat` first |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No USB found | Set `ROBIN_USB_DEST=…` or run `prepare-usb` with an explicit path |
| macOS blocks `.command` | Right-click → Open, or `chmod +x INSTALL_TO_USB.*` |
| Python / npm missing | Install Python 3.10+ and Node.js, then re-run |
| Stick full | Free space or use a larger drive |
| Want FAT32 | Prefer **exFAT**; FAT32 has 4 GB file limits |

## Related

- [usb/README.md](../usb/README.md) — kit layout and daily use  
- [ROBIN.md](ROBIN.md) · [research/PENDRIVE_AGENT_OS.md](research/PENDRIVE_AGENT_OS.md)
