# Plugins, tools, and APIs

## Where code lives

| Work | Repo / surface |
| --- | --- |
| New model runtime or tool (community) | https://github.com/langgenius/dify-plugins |
| Official plugin fixes/updates | https://github.com/langgenius/dify-official-plugins |
| Platform APIs, workflow/RAG/agent runtime | This monorepo (`api/core/`, controllers, services) |
| Agent runtime package | `dify-agent/` (see its `AGENTS.md` + `docs/dify-agent/`) |
| Typed CLI against the API | `cli/` (`difyctl`; read `cli/ARD.md` before new commands) |
| Language SDKs | `sdks/` |

Do not land third-party model/tool plugins inside the main monorepo unless the task is clearly platform-side.

## Product capabilities (for integration design)

- **Workflow**: visual canvas orchestration
- **RAG**: ingest → index → retrieve (PDF/PPT/common formats)
- **Agents**: Function Calling or ReAct + built-in/custom tools
- **Models**: hundreds of providers + OpenAI-compatible endpoints
- **LLMOps**: logs, annotations, prompt/dataset iteration
- **BaaS**: HTTP APIs for embedding Dify into product logic
- **Observability**: Langfuse, Opik, Arize Phoenix integrations (see docs)

## API / SDK usage patterns

- Prefer official docs: https://docs.dify.ai
- Prefer existing SDKs under `sdks/` over ad-hoc clients when integrating from Robin Igris or other apps.
- Auth: use app API keys / console tokens as documented; never commit secrets.
- For console UI work inside `web/`, call generated clients only (see [frontend.md](frontend.md)).

## `dify-agent` notes

- Commands from `dify-agent/`: `make check`, `make fix`, `make typecheck`, `make test`
- Local tests under `tests/local/` mirroring `src/`
- Do not use local mocks to claim real network/framework/serialization coverage
- Public runtime contract: `docs/dify-agent/`

## `difyctl` notes

- Leaf commands extend `DifyCommand`; shell in `index.ts`, behavior in sibling modules (`run.ts`, …)
- Behavior modules must not import `src/framework/`
- Tests use the real Hono mock under `cli/test/fixtures/dify-mock/` — no nock/msw/fetchMock
- Regenerate command tree: `pnpm tree:gen` / `pnpm tree:check` from `cli/`

## Pitfalls

- Inventing plugin APIs from memory — check official plugin repos and current docs.
- Mixing console (admin) APIs with app (end-user) APIs.
- Skipping tenant isolation when scripting against multi-workspace installs.
