# Cloudflare Containers + Neon

## GitHub Actions deployment

Pushing deployment changes to `ednai` runs `.github/workflows/deploy-cloudflare-neon.yml`.
It uses repository secrets `CLOUDFLARE_API_TOKEN`, `NEON_API_KEY`, and `HF_TOKEN`,
and repository variable `CLOUDFLARE_ACCOUNT_ID`. Optional `NEON_PROJECT_ID` selects
an existing **dedicated demo** project. Without it, the workflow creates/reuses
`ednai-cloudflare-demo` in London.
If your API key has access to multiple Neon organizations, set `NEON_ORG_ID` to
the desired organization ID; a single organization is selected automatically.
Optional `EDNAI_GRADIO_SPACE_ID` selects the existing model runtime. The default
remains `KoladeOdunope/ednai-natlas-runtime`.

The workflow preserves Render and deploys a separate public challenge/demo
account into Neon. It does not migrate Render users or balances or switch DNS.
This is not a real-customer deployment. GitHub Actions summarizes the resulting
workers.dev URL and Neon project. It validates readiness, demo login, and actual
model provenance. Model quota/access failure makes the job fail even if hosting
was created successfully. Cloudflare Containers access must be enabled.

Set optional secret `EDNAI_ADMIN_TOKEN` for a stable admin credential. Otherwise,
the workflow generates a new random admin token on every release and stores it
only inside the Cloudflare configuration secret. Credentials are not printed.
The deployment validates production-security, model-provider, and gateway tests;
the full suite still has the two documented beta-verification baseline failures.

Run the existing Python FastAPI gateway inside Cloudflare Containers behind a
Worker. Neon stores accounts, sessions, keys, wallets, usage, and beta evidence.
This requires a Cloudflare plan with Containers access; static Pages hosting
alone cannot run this application. The N-ATLaS Hugging Face runtime stays separate.

## Install and validate

From the repository root:

```bash
cd deploy/cloudflare
npm ci
npm test
npm run typecheck
npm run dry-run -- --containers-rollout none
```

This dry run skips image building and validates the Worker bundle and configuration, not database access
or successful container startup. Build the application separately from the root:

```bash
docker build -t ednai-cloudflare:$(git rev-parse HEAD) .
docker run --rm --entrypoint id ednai-cloudflare:$(git rev-parse HEAD) -u
```

## Provision and configure

1. In the intended Cloudflare account, enable Workers/Containers and identify
   the account ID and workers.dev subdomain. Authenticate Wrangler using
   `npx wrangler login` or a securely injected `CLOUDFLARE_API_TOKEN` and
   `CLOUDFLARE_ACCOUNT_ID`. Do not store account credentials in Git.
2. Create a Neon project near the selected deployment region and a dedicated
   database for this deployment. Use its PostgreSQL connection string with TLS
   (`sslmode=require` or stronger). A pooled connection is appropriate for the
   application's short-lived connections; use a direct connection for pg_dump
   and pg_restore. Keep demo and real-user databases separate.
3. Copy `config.example.json` into a secure file **outside this checkout**.
   Replace all placeholders, retain the existing approved billing rates, and
   set the actual hostname/origin. Reuse the current authenticated N-ATLaS
   provider settings. Transfer secrets through secure tooling, never chat.
4. Store the complete configuration as a Worker secret:

   ```bash
   npx wrangler secret put EDNAI_CONFIG < /secure/path/ednai-config.json
   ```

   Wrangler may require creating the Worker first. Use a staging deployment
   with no live traffic, then set its secret before making functional requests.
   The secret is forwarded only to the Python container. Configuration changes
   require restarting an existing container so it reads the new environment.
5. Run `npm run deploy`. Use the returned workers.dev hostname initially.
   For a custom domain, add a Worker custom-domain route and include the domain
   in TRUSTED_HOSTS and CORS_ORIGINS before directing traffic there.

One stable container instance is intentional: the application has an in-process
rate limiter. Container restarts reset that limiter; configure Cloudflare edge
rate limiting before a public launch. Do not increase max_instances without
distributed rate limiting. Durable Objects SQLite here is lifecycle metadata;
application data lives exclusively in Neon.

## Preserve Render data before cutover

Keep Render running during staging validation. Determine whether the existing
deployment uses PostgreSQL or SQLite before moving data. Do not assume the local
development database contains live accounts.

For PostgreSQL, freeze writes for the final export, take a protected backup using
pg_dump with the source's direct TLS connection, and restore it into an empty
Neon database using pg_restore with --no-owner --no-acl --exit-on-error. Supply
connection information through a protected pg_service.conf/.pgpass or secure
environment bindings. Do not print connection strings in logs. Validate table
counts, sample account/key lookup, ledger balances, and beta evidence before
starting traffic. Test restore procedures first on a disposable Neon branch.

For SQLite, obtain a consistent backup from the actual Render instance and use
an explicit reviewed SQLite-to-PostgreSQL data conversion. pg_restore cannot
import SQLite. Preserve IDs, password/key hashes, timestamps, ledger precision,
and foreign-key relationships; do not generate replacement accounts or credits.

## Release checks

- GET /health/live: 200, status=ok.
- GET /health/ready: 200, database and provider checks true.
- GET /, /developer, /guide/en, /v1/models, /v1/use-cases: 200.
- Sign in with a migrated account, inspect balance and existing scoped API keys.
- Run an authenticated generation and runtime probe; verify NCAIR1/N-ATLaS
  provenance and exact token usage. These requests consume inference quota.
- Verify Secure cookies, HTTPS, trusted hosts, CORS, and forwarded client IP.
- Check database counts/balances again and take a Neon backup/restore checkpoint.

Set GitHub repository variable EDNAI_BASE_URL to the new HTTPS origin and secret
EDNAI_SMOKE_API_KEY to a scoped test-account API key for live smoke workflows.
Switch DNS/client traffic only after these checks pass. Keep Render available
for rollback. After new writes reach Neon, rolling back also requires a data
reconciliation plan; do not send traffic to a stale source database.

Local validation does not prove account provisioning, cloud deployment, data
migration, or DNS cutover. Record each of those outcomes separately.
