# Frontend (`web/`, `packages/dify-ui/`)

Package guide: `web/AGENTS.md`. Install JS deps from the **repo root** workspace (`pnpm install`), then run scripts with `pnpm -C web …`.

## Dev

```bash
cp web/.env.example web/.env.local
pnpm install
pnpm -C web run dev            # Next.js
pnpm -C web run dev:vinext     # preferred DX
pnpm -C web run dev:proxy      # optional online API proxy (see web/dev-proxy.config.ts)
```

Or root: `pnpm dev` (vinext + proxy). App: http://localhost:3000 · Storybook: `pnpm -C web storybook` → :6006.

Node `^22.22.1`; enable Corepack for pnpm version pinning.

## Package contracts

- **i18n**: user-facing strings via `web/i18n/en-US/` keys; update every supported locale on add/rename.
- **API clients**: generated `consoleQuery` / `consoleClient` from `@/service/client`. No handwritten REST helpers, DTO mirrors, mock-backed app state, or edits to generated contracts.
- **UI**: prefer `@langgenius/dify-ui/*` primitives, data attributes, and design tokens. Keep a visible focus indicator on the final focusable element.
- **Overlays**: follow `web/docs/overlay.md`; migrate a legacy overlay only when the change touches that boundary.
- **Icons**: custom SVG via `packages/iconify-collections/README.md` — do not add generated React icons under `app/components/base/icons/src/`.

## Skill routing (upstream)

| Need | Skill / doc |
| --- | --- |
| Component ownership, state, data flow, effects, interactions | `.agents/skills/how-to-write-component` |
| Vitest / RTL | `.agents/skills/frontend-testing` + **`web/docs/test.md`** (policy owner) |
| Explicit review/audit | `.agents/skills/frontend-code-review` |
| Lint policy | `web/docs/lint.md` when changing/running static checks |

Skills may route and execute `web/docs/test.md` policy but must not redefine it.

## Component defaults (summary)

| Question | Default |
| --- | --- |
| Where does code live? | Product workflow / route / feature owner |
| Who owns state/handlers? | Lowest visual owner that consumes them |
| Jotai? | Local state first; promote when siblings need one source of truth |
| URL state? | Next.js route APIs + `nuqs` |
| Remote state? | TanStack Query at lowest consumer |
| Effects? | Derive in render or handle the user action; Effect only to sync a named external system |

## Pitfalls

- Cookie domain must align when API and web sit on different subdomains.
- Set `NEXT_PUBLIC_API_PREFIX` and `NEXT_PUBLIC_PUBLIC_API_PREFIX` correctly in `.env.local`.
- Docker image builds for web use **repo root** as build context: `docker build -f web/Dockerfile -t dify-web .`
