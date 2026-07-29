# Backend (`api/`)

Package guide: `api/AGENTS.md`. Run commands from the **repository root** unless noted.

## Commands

| Goal | Command |
| --- | --- |
| Format + lint + contracts | `make lint` |
| Type check | `make type-check` |
| Unit tests | `make test` |
| Targeted tests | `make test TARGET_TESTS=./api/tests/<path>` |
| Arbitrary Python | `uv run --project api <command>` |

Direct alternatives inside `api/`: `uv run pytest`, `uv run ruff check --fix ./`, `uv run ruff format ./`, `uv run pyrefly check`.

Integration suites that need Docker are normally CI-owned. Do not start long-running API/worker processes unless the user asked for a running stack.

## Architecture boundaries

- **Controllers**: transport parse/serialize only.
- **Services**: orchestration.
- **`core/`** (or domain owner): policy and domain behavior.
- **`libs/`**: business-agnostic utilities; reuse existing owners before new abstractions.
- Config: `configs.dify_config`
- Storage: `extensions.ext_storage.storage`
- Outbound HTTP: SSRF-safe owner `core.helper.ssrf_proxy`
- Async work: existing Celery task/queue owners — do not shove unrelated jobs into workflow-specific services.
- Retriable Celery tasks must be idempotent; log affected resource IDs.

## Multi-tenancy and data

- Scope tenant-owned reads/writes by the **complete owner chain**.
- Propagate `tenant_id` across every affected layer.
- After payload or async boundaries, reconstruct trusted internal references from validated DB state.
- Keep write transactions explicit and bounded; avoid external I/O inside an open transaction unless a documented consistency contract requires it.

## Schemas and APIs

- Pydantic v2 for request/response models.
- Before changing controller schemas, generated API contracts, or `SystemFeatureModel`, read `controllers/API_SCHEMA_GUIDE.md`.
- `/system-features` is a minimal unauthenticated bootstrap allowlist — not a general config registry.
- Reuse domain exceptions; translate at the controller boundary.
- OpenAPI / TS stubs: see `api/README.md` (`uv run dev/generate_swagger_specs.py …`).

## Local contracts

Read surrounding module/class/function docstrings and non-obvious comments before changing behavior. Update them only when the owned behavior changes.

For explicit review/audit requests, use `.agents/skills/backend-code-review` and its `references/*-rule.md` packs.
