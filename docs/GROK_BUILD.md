# Grok Build × Robin Igris

Integrate **[Grok Build](https://github.com/xai-org/grok-build)** (SpaceXAI’s
terminal coding agent) as Robin’s **coding sidecar**.

| | Robin | Grok Build |
|--|-------|------------|
| Role | Pendrive-native mind (graph + metabolism) | Deep code edits / TUI agent |
| Runs | On the stick (Carry / AOS) | `grok` CLI (host or USB PATH) |
| Auth | Local / Manifest | `XAI_API_KEY` or browser OAuth |

We do **not** vendor the Rust monorepo into this repo (large workspace). Robin
calls the released `grok` binary. Upstream pin: `SOURCE_REV`
`2a818575225183d8ca915f5632a09b8067b5156a`.

## Install

```bash
./scripts/install-grok-build.sh
# or: curl -fsSL https://x.ai/cli/install.sh | bash
export XAI_API_KEY=xai-...   # or run `grok` once for OAuth
grok --version
```

Build from source (optional): see upstream README — needs Rust + DotSlash.

## Use with Robin

```bash
# AOS shell
:grok
:grok explain the auth flow in aos/kernel.py

# Tools
grok_status
grok_ask prompt="List TODOs in robin_igris/"
grok_code task="Fix the failing test in test_routing.py"
```

Headless equivalent:

```bash
grok -p "Your prompt" --cwd /path/to/USB/ROBIN_IGRIS/app --no-auto-update
```

## Env

| Variable | Meaning |
|----------|---------|
| `XAI_API_KEY` | API auth (CI / no browser) |
| `GROK_BIN` / `ROBIN_GROK_BIN` | Path to `grok` binary |
| `ROBIN_GROK_MODEL` | Model id (default `grok-build`) |
| `ROBIN_GROK_YOLO` | `1` = `--yolo` auto-approve tools |
| `ROBIN_GROK_MAX_TURNS` | Headless turn cap |
| `ROBIN_GROK_TOOLS` / `ROBIN_GROK_DISALLOWED_TOOLS` | Tool allow/deny lists |

Manifest: `grok_build.enabled` · tools `grok_*`.

## Docs

- Upstream: [x.ai/cli](https://x.ai/cli) · [docs.x.ai/build](https://docs.x.ai/build/overview)
- Headless: `grok -p` ([user guide §14](https://github.com/xai-org/grok-build/blob/main/crates/codegen/xai-grok-pager/docs/user-guide/14-headless-mode.md))
