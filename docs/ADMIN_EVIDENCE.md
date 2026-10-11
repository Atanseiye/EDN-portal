# Developer validation evidence

Share `/feedback` with external developers. `/challenge` retains its existing demo-session access rules and includes the expanded form and admin link.

Open `/challenge/admin` and sign in with the deployment's `EDNAI_ADMIN_TOKEN` (a strong random secret, at least 32 characters). Never share this token with testers. The admin session uses a signed, HttpOnly, SameSite Strict cookie, expires after one hour and uses Secure over HTTPS. Sign out clears the browser cookie; rotating the token invalidates all issued sessions.

The dashboard polls every 15 seconds and lists all consented records. Review external status and actual supporting evidence before clicking Verify. Legacy feedback needs a new expanded submission. Counts deduplicate tester identifiers and distinguish submissions from verified external testers. Export PDF and JSON from the protected dashboard; downloads are freshly generated snapshots, not continually changing files. Pending/internal evidence is a clearly separated PDF appendix.

The PDF omits names and raw tester identifiers, but affiliation, role and submitted free text remain. Review/redact sensitive data before submission. Portable PDF fonts transliterate text; JSON retains original Unicode. This is validation evidence, not independent proof of live N-ATLaS integration. Failed and partial tests remain documented.

## Deployment

Normal Python server startup migrates SQLite/PostgreSQL automatically. Cloudflare skips DB initialization: apply `deploy/cloudflare/beta_evidence_migration.sql` to Neon before deploying. Use persistent PostgreSQL for deployed feedback; local SQLite at `/tmp` is not durable cloud storage. Confirm trusted hosts/CORS include the actual deployment origin. Existing admin bearer-token APIs remain available for automation.
