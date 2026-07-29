# USB layout — born-for-pendrive partitions

Target layout (physical or directory simulation on exFAT):

```
ROBIN_IGRIS/
  boot/          # bootloader notes / Live ISO (immutable seed path)
  core/          # signed immutable root (future microkernel image)
  shell/   → data/shell/     # evolving runtime checkpoints, skills, policy
  soul/    → data/aos/soul/  # PAM identity + memory
  queue/   → data/queue/     # offline outbox (Buzz, sync)
  app/                       # userspace AOS + companion (bridge era)
  runtime/                   # portable Python / OmniRoute hooks
```

Today `scripts/prepare-usb.sh` creates `data/{aos,shell,queue,home,system3}`.
Core updates (future) accept **only** a second signed USB — never WiFi.
