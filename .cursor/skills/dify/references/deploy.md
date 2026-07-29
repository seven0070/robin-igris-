# Deploy and operate Dify

## Requirements

- CPU ≥ 2 cores, RAM ≥ 4 GiB
- Docker + Docker Compose **v2.24.0+** for the default path

## Production-style Compose

```bash
cd docker
cp .env.example .env
# Optional advanced vars: copy themed files from envs/ (drop .example suffix)
docker compose up -d
```

- Install UI: http://localhost/install
- Essential defaults live in `docker/.env.example`; advanced knobs in `docker/envs/` by theme.
- Compose loads `envs/*.env` when present, then `.env` (`.env` wins).
- Vector store: set `VECTOR_STORE` in `.env` (`weaviate`, `milvus`, `opensearch`, …). See `envs/vectorstores/`.
- SSL: `docker/certbot/README.md`
- OTEL: copy `envs/core-services/shared.env.example` → `shared.env`, set `ENABLE_OTEL=true` and `OTLP_BASE_ENDPOINT`

Env sync helper (when maintaining a full custom `.env`): `docker/dify-env-sync.sh` / `dify-env-sync.py`.

Do **not** dump optional/provider-specific vars into root `.env.example`; put them under the matching `envs/*.env.example`.

## Dev middleware only

```bash
cd docker
cp envs/middleware.env.example middleware.env
docker compose --env-file middleware.env -f docker-compose.middleware.yaml -p dify up -d
```

Or from repo root: `make prepare-docker` / `./dev/start-docker-compose`.

## Cloud / enterprise

- Hosted: https://dify.ai
- Docs: https://docs.dify.ai
- Community K8s/Helm/Terraform options are listed in the root README (third-party charts).
- Enterprise inquiries: business@dify.ai

## Pitfalls

- After `.env` changes, re-run `docker compose up -d` from `docker/`.
- Frontend + backend on different subdomains need shared cookie domain (`COOKIE_DOMAIN` / `NEXT_PUBLIC_COOKIE_DOMAIN`).
- Generate a strong `SECRET_KEY` for any non-throwaway deploy.
- FAQ: https://docs.dify.ai/getting-started/install-self-hosted/faqs
