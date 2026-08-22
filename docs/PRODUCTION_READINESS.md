# Production Readiness

## Current status

The project is a good modular-monolith MVP foundation, but it should be treated as pre-production. It has clear layering, migrations, tests, Docker packaging, and safe provider stubs, but it still needs operational work before running on a VPS with real users.

Current architecture:

```text
Telegram / HTTP
  -> handlers / routes
  -> application services
  -> repositories
  -> PostgreSQL / Redis / provider abstractions
```

No real VPN provider, real payment provider, Telegram webhook, microservices, Kubernetes, or background worker has been added.

## Security status

Improved:

- `.dockerignore` excludes `.env`, caches, tests, docs, and build artifacts from Docker context.
- Production mode now fails fast when critical values are missing or unsafe.
- `SECRET_KEY` must be at least 32 characters in production.
- `BOT_TOKEN` is required in production.
- `SUBSCRIPTION_BASE_URL` must be HTTPS in production.
- `ALLOWED_HOSTS` must be explicit in production.
- FastAPI docs/openapi are disabled in production.
- Trusted host checks and basic HTTP security headers are enabled.
- Happ subscription token format is validated before DB lookup.
- User-provided text rendered in Telegram HTML messages is escaped.
- Admin authorization remains based only on Telegram ID.
- Admin `/extend` now has a configured maximum day limit.
- Docker runtime user is non-root.

Remaining risks:

- If the local `.env` contains real `BOT_TOKEN` or `SECRET_KEY`, rotate them manually. This file is ignored by Git, but local secrets can still leak through backups, screenshots, sync tools, or copied archives.
- No edge rate limiting yet.
- No production reverse proxy/TLS configuration yet.
- No security monitoring/alerting yet.
- No dependency vulnerability scanning in CI yet.
- Subscription URLs are bearer tokens; anyone with the URL can fetch the subscription while it is active.

## Database status

Improved:

- `telegram_id` is unique at DB level.
- Subscription token is unique at DB level.
- Payment provider transaction ID is unique at DB level.
- Foreign keys are present.
- Status columns now have DB check constraints through migration `0003_add_status_check_constraints`.
- Concurrent mutation paths now use PostgreSQL row locks where current architecture needs serialization.

Remaining risks:

- Unit tests still run on SQLite, so PostgreSQL-specific lock behavior is not fully covered.
- There is no backup/restore process yet.
- There is no migration rollback drill yet.

## Testing status

Current result:

```text
27 passed
```

Added coverage:

- production config validation;
- FastAPI docs disabled in production;
- malformed subscription token rejection before DB lookup;
- readiness endpoint success/failure;
- blocked user cannot receive or activate subscription;
- admin authorization based on Telegram ID;
- admin `/extend` bounds;
- concurrent user creation contract.

Remaining gaps:

- PostgreSQL integration tests for real row-lock behavior;
- Telegram API failure simulation;
- Redis outage integration behavior;
- Docker Compose runtime smoke test with real Postgres container;
- migration apply/rollback against disposable Postgres.

## Docker status

Improved:

- App image builds successfully.
- Docker build context now excludes `.env` via `.dockerignore`.
- Runtime user is non-root.
- Entrypoint uses `exec` for graceful signal handling.
- App image has a healthcheck.
- Compose adds restart policies and healthchecks.
- PostgreSQL and Redis ports bind to `127.0.0.1`, not all interfaces.

Remaining risks:

- Compose is still suitable for single-host MVP, not full production operations.
- Database password in `docker-compose.yml` is development-grade and must be replaced via environment/secrets for real deployment.
- No backup volume strategy is defined.

## Known limitations

- Payment provider is a stub.
- VPN provider is a mock.
- Telegram bot uses polling, not webhook.
- No user-facing rate limiting.
- No audit log.
- No production monitoring stack.
- No real server provisioning or subscription payload generation.

## Remaining risks

- Bearer-token subscription URL can be leaked by user copy/paste or device logs.
- Payment idempotency is structurally improved, but real provider behavior is not implemented or tested.
- The current admin interface is minimal and command-based.
- Tests do not yet prove behavior under real PostgreSQL isolation.
- Production deployment still needs TLS, firewall, backup, monitoring, and secrets management.

## What must be done before VPS

- Create a real `.env` for VPS with `APP_ENV=production`.
- Use strong `SECRET_KEY`.
- Set real `BOT_TOKEN`.
- Set HTTPS `SUBSCRIPTION_BASE_URL`.
- Set explicit `ALLOWED_HOSTS`.
- Replace development DB password.
- Put app behind a reverse proxy with TLS.
- Restrict inbound firewall ports.
- Configure persistent Postgres backup.
- Run migrations against the VPS database.

## What can wait until after VPS

- Telegram webhook migration.
- Full web admin panel.
- Advanced analytics.
- Distributed tracing.
- Kubernetes or any orchestration beyond Docker Compose.
- Complex referral/promo/billing features.

## What must be done before first paying customer

- Implement a real payment provider with signed callbacks.
- Add payment callback idempotency integration tests against PostgreSQL.
- Add refund/failure handling policy.
- Implement real VPN provider integration.
- Verify subscription URL payload in Happ.
- Add customer-support operational process.
- Add backup restore test.

## What must be done before 1,000 users

- Add edge or Redis-backed rate limiting for public endpoints and bot actions.
- Add PostgreSQL integration test suite.
- Add production logging/alerts.
- Add dependency vulnerability scanning.
- Review DB pool sizes and Postgres resource limits.
- Add basic abuse monitoring for subscription URL requests.

## What must be done before 10,000 users

- Add stronger observability: metrics, dashboards, alerts.
- Add automated backups with restore drills.
- Add load testing for `/s/{token}` and bot flows.
- Add separate deployment environments.
- Consider webhook only if polling becomes operationally limiting.
- Review whether Redis-backed FSM and rate limiting are sufficient.
- Revisit database indexes from production query patterns.
