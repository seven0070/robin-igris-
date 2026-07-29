# Building a Live USB where Agent OS is the only session

PNAOS is a **userspace Agent Operating System**. For a true “boot from stick”
experience, pair it with a minimal Linux Live image.

## Recommended stack

1. **Ventoy** on the 128GB stick (multi-ISO).
2. A small **Debian Live** or **Ubuntu Server** ISO (~1–2GB).
3. Our **ROBIN_IGRIS** overlay prepared by `scripts/prepare-usb.sh`.

## Session takeover (agent is the shell)

On the Live system, disable the desktop and auto-start AOS:

```bash
# After Live boot, or via persistence overlay:
sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
cat <<'EOF' | sudo tee /etc/systemd/system/getty@tty1.service.d/override.conf
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin robin --noclear %I $TERM
EOF

# ~/.bash_profile for user robin:
export ROBIN_USB_ROOT=/media/robin/ROBIN_IGRIS
cd "$ROBIN_USB_ROOT"
exec ./aos-boot.sh
```

`aos-boot.sh` runs `python -m aos.boot` — avatar UI only; no desktop.

## Windows / macOS (borrowed host OS)

Without Live Linux, `LAUNCH.bat` / `launch.sh` already treat the stick as home
and the PC as display. Use **AOS mode**:

```bat
set ROBIN_AOS_MODE=1
AOS_BOOT.bat
```

or `./aos-boot.sh`.

## Unplug semantics

AOS installs SIGINT/SIGTERM/atexit handlers that **seal the soul Merkle tip**
before exit. Yanking power still risks last-second loss — prefer STOP / Ctrl+C,
then eject. Future work: USB power-loss journal flush via hardware interrupt.

## Size

| Component | Size |
|-----------|------|
| Ventoy + Live ISO | ~2–4 GB |
| Robin AOS kit | ~0.5–2 GB |
| Soul + data | grows |
| Free on 128GB | ~100GB+ for local models |
