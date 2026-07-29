---
name: dify
description: Develop, self-host, review, and integrate with Dify (langgenius/dify) — LLM app platform for workflows, RAG, agents, and model management. Use when working on the Dify monorepo (api/, web/, docker/, dify-agent/, cli/, e2e/), self-hosting Dify, writing Dify plugins/tools, calling Dify APIs/SDKs, or when the user mentions Dify, dify.ai, or dify-plugins.
---

# Dify

Open-source LLM app platform: visual workflows, RAG pipelines, agents, model providers, and BaaS APIs.

Upstream: https://github.com/langgenius/dify · Docs: https://docs.dify.ai

## Monorepo map

| Path | Role |
| --- | --- |
| `api/` | Flask/Python backend (uv). Core domain under `api/core/` |
| `web/` | Next.js / vinext frontend (pnpm workspace) |
| `docker/` | Compose deploy + middleware for local dev |
| `dify-agent/` | Standalone agent backend (uv) |
| `cli/` | `difyctl` TypeScript CLI |
| `e2e/` | Cucumber + Playwright |
| `packages/dify-ui/` | Shared UI primitives |
| `sdks/` | Client SDKs (e.g. nodejs, php) |
| `.agents/skills/` | Upstream agent skills (review, components, e2e) |

Follow the **nearest scoped `AGENTS.md`** for the files being changed. Root `AGENTS.md` / `CLAUDE.md` are entry points only.

## Route the task

| Intent | Do this |
| --- | --- |
| Self-host / operate | Read [references/deploy.md](references/deploy.md) |
| Backend change under `api/` | Read [references/backend.md](references/backend.md) |
| Frontend under `web/` or `packages/dify-ui/` | Read [references/frontend.md](references/frontend.md) |
| Plugins, tools, model runtimes, public API | Read [references/plugins-api.md](references/plugins-api.md) |
| Explicit backend review | Use upstream skill `.agents/skills/backend-code-review` |
| Explicit frontend review | Use upstream skill `.agents/skills/frontend-code-review` |
| Component ownership / state / data flow | Use `.agents/skills/how-to-write-component` |
| Vitest / RTL tests | Use `.agents/skills/frontend-testing` + `web/docs/test.md` |
| E2E under `e2e/` | Use `.agents/skills/e2e-cucumber-playwright` |

## Hard gotchas

- Backend Python commands: `uv run --project api <command>` (from repo root) or `make` targets.
- Backend integration tests are CI-owned; do not treat them as a local default.
- Do not start long-running services as routine agent work unless the user asked to run the stack.
- Frontend i18n: user-facing strings go through `web/i18n/en-US/` keys; update every supported locale when adding/renaming keys.
- New/migrated backend calls from web: use generated `consoleQuery` / `consoleClient` from `@/service/client` — no handwritten REST helpers or DTO mirrors.
- Prefer `@langgenius/dify-ui/*` primitives and design tokens.
- Plugins live in separate repos: [dify-plugins](https://github.com/langgenius/dify-plugins) (community) and [dify-official-plugins](https://github.com/langgenius/dify-official-plugins).
- Security reports → `security@dify.ai`, not public GitHub issues.

## Quick commands (source checkout)

```bash
# One-shot local stack (Docker)
cd docker && cp .env.example .env && docker compose up -d
# Dashboard: http://localhost/install

# Dev from source (recommended scripts)
./dev/setup
./dev/start-docker-compose   # PG/Redis/Weaviate middleware
./dev/start-api
./dev/start-web              # http://localhost:3000
./dev/start-worker           # async tasks

# Or Makefile helpers
make dev-setup               # middleware + web install + api uv sync/migrate
make lint                    # api format/lint/contracts
make test TARGET_TESTS=./api/tests/<path>
```

Node: `^22.22.1` (see `.nvmrc`). Package manager: `pnpm` (workspace at repo root).

## Contribution rules of thumb

1. Open/link an issue before substantial PRs (`fixes #<n>`).
2. Add focused tests when behavior or regression risk changes.
3. Model/tool plugins → plugin repos, not this monorepo.
4. Keep transport in controllers, orchestration in services, policy in `core/` (or its domain owner).

## Sources

Distilled from Dify `AGENTS.md` files, `CONTRIBUTING.md`, `api/README.md`, `web/README.md`, `docker/README.md`, and `.agents/skills/*` on https://github.com/langgenius/dify.
