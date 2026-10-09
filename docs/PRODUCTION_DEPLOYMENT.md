# EDNAi Production Deployment Baseline

This document defines the minimum deployment standard for serving real EDNAi developers.

The target hosting platform is now Cloudflare Containers with Neon PostgreSQL.
Follow [the Cloudflare deployment and migration guide](../deploy/cloudflare/README.md)
for platform-specific commands, secret injection, and cutover checks. The Azure
examples below describe the existing security baseline and are not the new
deployment instructions.

## Environment separation

Use separate deployments and databases for:

- **demo/challenge** — may explicitly enable the shared `demo@edn.com` account;
- **production** — real developer accounts only.

Never point demo and production at the same database.

Production must use:

```text
APP_ENV=production
EDNAI_AUTH_ENABLED=true
EDNAI_DEMO_ACCOUNT_ENABLED=false
EDNAI_ALLOW_PUBLIC_DEMO_ACCOUNT=false
EDNAI_PRICING_MODE=production
EDNAI_REQUIRE_EXACT_USAGE=true
```

EDNAi refuses to start in production if required security settings are missing.

## Runtime architecture

Recommended path:

```text
Internet
  -> Azure Front Door / API Management
  -> Azure Container Apps
       -> EDNAi FastAPI
       -> Azure Database for PostgreSQL
       -> authenticated N-ATLaS runtime
```

The application container does not contain model weights. The N-ATLaS runtime remains an explicit provider boundary.

## Secrets

Store these in Azure-managed secrets / Key Vault and expose them to the Container App only as secret references:

- `HF_TOKEN`
- `EDNAI_ADMIN_TOKEN`
- `EDNAI_DATABASE_URL`
- payment-provider secrets when added

Never commit secrets, put them in Docker build arguments, or return them to browser clients.

Rotate production secrets after staff changes, suspected exposure, and on a scheduled operational cadence.

## Database

Production requires PostgreSQL through `EDNAI_DATABASE_URL`.

Ephemeral SQLite under `/tmp` is deliberately rejected when `APP_ENV=production`.

Enable:

- TLS to the database;
- automated backups;
- point-in-time recovery where available;
- restricted network access;
- least-privilege database credentials;
- regular restore tests.

Developer wallet updates, token-usage records and ledger entries are transactional. Do not bypass those tables with manual balance edits.

## Container

The repository Dockerfile:

- runs as an unprivileged UID;
- installs only server dependencies;
- exposes port 8080;
- defines a liveness health check;
- starts a single Uvicorn worker.

Scale with Container Apps replicas rather than multiple workers inside one container unless load testing proves another configuration is required.

Deploy immutable images identified by commit SHA. Do not deploy a mutable `latest` image as the only rollback reference.

## Probes

Configure Azure Container Apps:

```text
Liveness:  GET /health/live
Readiness: GET /health/ready
```

Liveness only establishes that the process is responsive.

Readiness verifies durable storage and that a qualifying N-ATLaS provider is configured. It intentionally does not consume GPU quota.

## Network and browser security

Production must set explicit values:

```text
TRUSTED_HOSTS=<azure-fqdn>,<custom-domain>
CORS_ORIGINS=https://<custom-domain>
```

Wildcard trusted hosts or wildcard CORS cause production startup validation to fail.

EDNAi adds:

- HSTS in production;
- Content-Security-Policy;
- X-Content-Type-Options;
- frame denial;
- referrer policy;
- permissions policy;
- request IDs;
- HttpOnly + Secure + SameSite=Strict session cookies.

## Authentication

Real accounts require normal developer registration.

Passwords and API keys are never stored in plaintext.

API keys are independently revocable and scope-limited.

The public challenge credential:

```text
demo@edn.com
12345
```

must exist only in a dedicated demo deployment. Production startup refuses this configuration unless an operator explicitly overrides the safeguard.

## Rate limiting

EDNAi includes a per-instance fallback limiter for authentication and developer API calls.

For multi-replica production, enforce global limits at Azure API Management / Front Door or a shared Redis-backed limiter. Do not rely on an in-process limiter as the only distributed abuse control.

Recommended categories to configure independently:

- registration/login;
- generation/chat;
- Use Case Studio;
- ASR uploads;
- evaluation runs;
- administrative APIs.

## Token billing

Billable generation requires exact token usage.

The N-ATLaS runtime returns tokenizer-derived:

```text
prompt_tokens
completion_tokens
total_tokens
```

If a production provider does not return exact token counts, EDNAi refuses to estimate and bill the request.

Pricing is server configuration and is never accepted from clients.

Wallet deductions and usage ledger writes are atomic.

## API keys

Limit API-key creation per account and encourage one key per application/environment.

Recommended scopes:

```text
inference.generate
inference.chat
usecases.run
speech.transcribe
evaluation.run
dataset.inspect
finetuning.plan
```

Never log complete API keys or bearer tokens.

## Observability

Send stdout/stderr to Azure Log Analytics / Application Insights.

Every HTTP response includes `X-Request-ID`; use it to correlate application logs and support cases.

Alert on:

- elevated 5xx rates;
- repeated 401/403/429 responses;
- database readiness failures;
- N-ATLaS provider quota/failure rates;
- unusual token spend;
- wallet-credit administration;
- container restarts.

Do not log passwords, session cookies, HF tokens, admin tokens or complete developer API keys.

## CI/CD

Before deployment, CI must pass:

- Python compilation;
- Python tests;
- dependency consistency;
- TypeScript typecheck/build;
- browser JavaScript syntax check;
- production Docker image build;
- non-root container verification.

Use GitHub -> Azure authentication through OIDC/federated credentials rather than a long-lived Azure password or service-principal secret.

Protect the production environment with branch/environment approval rules if the repository plan supports them.

## Rollout and rollback

Use Azure Container Apps revisions.

A production release should:

1. build an immutable image tagged with the Git commit;
2. deploy a new revision;
3. wait for readiness;
4. run health and authenticated API smoke tests;
5. move traffic to the new revision;
6. keep the prior revision available for immediate rollback.

Do not delete the previous hosting environment until Azure has been proven stable.

## Launch gates still external to the repository

Before charging public users at scale, complete:

- production PSP integration and verified webhook handling;
- commercial pricing approval;
- privacy policy / terms appropriate to the operating entity;
- support/contact process;
- email verification and account-recovery mechanism;
- distributed edge rate limiting;
- Azure database backup/restore test;
- load test at the intended concurrency.

The repository now provides the application security baseline, but these operational/commercial controls must also be in place before declaring a public paid launch.
