# Cloudflare Workers Free + Neon

The gateway runs as a Python Worker using Cloudflare's FastAPI/ASGI support.
There is no container, Docker deployment, or paid Workers requirement. Neon
provides PostgreSQL and the existing Hugging Face Space provides N-ATLaS inference.
All services remain subject to their free-tier quotas.

## GitHub CI/CD

Pushes to `ednai` run `.github/workflows/deploy-cloudflare-neon.yml`.
Required repository secrets: `CLOUDFLARE_API_TOKEN`, `NEON_API_KEY`, `HF_TOKEN`.
Required repository variable: `CLOUDFLARE_ACCOUNT_ID`.

Optional variables: `NEON_PROJECT_ID` for a dedicated demo project,
`NEON_ORG_ID` when multiple organizations are accessible, and
`EDNAI_GRADIO_SPACE_ID` to select the existing official model runtime.
Without a project ID, CI creates/reuses `ednai-cloudflare-demo` in London.
The model default is `KoladeOdunope/ednai-natlas-runtime`.

CI stages the repository Python modules, resolves Workers-compatible packages,
validates the bundle, provisions Neon, initializes the existing schema and demo
account, deploys the Worker, installs the server configuration as a Worker secret,
and checks database readiness, pages, login, and real N-ATLaS model provenance.
Credentials are never committed. Optional secret `EDNAI_ADMIN_TOKEN` preserves a
stable admin token; otherwise CI rotates a randomly generated admin token each release.

The deployment keeps Render's data and traffic unchanged. It uses a separate
public demo database; never point it at a real-customer database. Cutover and
migration of existing accounts require a protected export, restore, and balance/
ledger verification before changing client URLs or DNS.

## Runtime adaptation

- `server/postgres.py` selects pg8000 on Workers and psycopg on normal hosts.
  Both retain commit/rollback transactions and enforce TLS; wallet operations
  are not split into independent HTTP queries.
- Neon `pgcrypto` performs password PBKDF2 at the existing 310,000 iterations,
  preserving salt/hash compatibility. CI checks it against Python's derivation
  before deploying. WebCrypto supplies PostgreSQL's lower-cost SCRAM derivation.
  Cloudflare's 100,000-iteration WebCrypto limit is respected.
- Gradio uses its HTTP/SSE API without native clients or background threads.
  Model provenance and exact usage checks remain in the shared provider code.
- Repository pages/assets use the Workers static-assets binding.
- The framework loads during isolate startup; database schema creation and demo
  seeding run in CI rather than spending the request CPU budget.

## Local setup

From the repository root:

```bash
python scripts/prepare_python_worker.py
cd deploy/cloudflare
npm ci
uv run pywrangler deploy --dry-run
uv run pywrangler dev
```

Python Workers dependencies are resolved against the official Pyodide package
index. The generated `runtime/` directory and virtual environments are ignored.
Use a local `.dev.vars` file for `EDNAI_CONFIG`; do not commit credentials.
`config.example.json` shows the production/demo configuration shape. Cloudflare
stores the real configuration as a Worker secret. The existing container Worker
Durable Object is removed by the v2 migration; it never stored application data.

Free-tier CPU, request, subrequest, Neon compute/storage and Hugging Face GPU
quotas can reject traffic. Readiness verifies configuration/storage; the CI model
probe verifies real inference separately and fails when inference quota is exhausted.
The full Python suite has two pre-existing beta-verification failures. Deployment
checks cover adapters, security, model identity, and the gateway; no assertions are disabled.
