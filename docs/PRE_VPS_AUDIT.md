# Final Pre-VPS Audit

This audit treats Baza VPN as a commercial pre-production MVP. The project is not production-ready yet, even with a passing test suite.

## Scope

Reviewed areas:

- architecture, SOLID, separation of concerns, dependency inversion;
- SQLAlchemy async, PostgreSQL compatibility, Alembic migrations;
- transaction boundaries, `SELECT FOR UPDATE`, unique constraints, idempotency;
- Telegram handlers, callback handling, admin commands, error handling;
- security, secret management, input validation, HTML injection, token security;
- Dockerfile, Docker Compose, networking, runtime user;
- Redis usage, health/readiness, graceful shutdown;
- tests, test isolation, SQLite vs PostgreSQL gaps;
- dependency and supply-chain posture;
- resource exhaustion, abuse prevention, data consistency.

## Architecture Summary

Current architecture is appropriate for pre-VPS modular monolith:

```text
Telegram / HTTP
  -> aiogram handlers / FastAPI routes
  -> application services
  -> repositories
  -> PostgreSQL / Redis / external provider abstractions
```

The project should not move to microservices, Kubernetes, webhook Telegram delivery, real payments, or real VPN servers before the current MVP is stable on a VPS.

## Findings

### HIGH: Telegram bot and FastAPI run in one process

- FILE: `app/main.py`, `docker-compose.yml`
- LOCATION: `lifespan()`
- PROBLEM: FastAPI and polling bot start together. Scaling `app` replicas would start multiple bot consumers with the same token.
- WHY: Telegram polling must have exactly one active consumer per token.
- FIX: Do not scale `app` above one replica before redesign. Later split `api` and `bot` processes or move to webhook intentionally.
- TEST: Deployment-level smoke test ensuring one bot consumer process.
- STATUS: Not fixed now. This would change deployment architecture and is not needed for a single VPS MVP.

### HIGH: Local `.env` may contain real secrets

- FILE: `.env`
- LOCATION: project root
- PROBLEM: A local `.env` can contain real `BOT_TOKEN` and `SECRET_KEY`.
- WHY: `.gitignore` protects Git, but not backups, screenshots, sync tools, archives, or accidental Docker context if ignore rules regress.
- FIX: Rotate real secrets manually, keep `.env` local-only, use VPS environment variables or secrets.
- TEST: Secret scanning in CI excluding `.env.example`.
- STATUS: Not changed automatically. Secrets must be rotated outside code.

### MEDIUM: Docker Compose had explicit development DB credentials

- FILE: `docker-compose.yml`, `.env.example`, `app/config.py`
- LOCATION: `postgres.environment`, `app.environment`, production config validation
- PROBLEM: `baza:baza` was easy to copy to production.
- WHY: Weak default DB credentials are a common production misconfiguration.
- FIX: Use environment interpolation with a local-only fallback, document strong password, reject weak production DB passwords.
- TEST: `test_production_rejects_development_database_password`.
- STATUS: Fixed.

### MEDIUM: SQLAlchemy logs could expose parameters

- FILE: `app/database.py`
- LOCATION: `create_engine()`
- PROBLEM: Engine did not set `hide_parameters=True`.
- WHY: SQL parameters and connection details can appear in logs under failures/debugging.
- FIX: Add `hide_parameters=True`.
- TEST: Covered by config/engine construction indirectly; log redaction integration test should be added later.
- STATUS: Fixed.

### MEDIUM: No explicit DB pool tuning

- FILE: `app/config.py`, `app/database.py`
- LOCATION: `Settings`, `create_engine()`
- PROBLEM: PostgreSQL pool size, overflow, recycle and command timeout were not configurable.
- WHY: VPS resource limits need predictable DB connection behavior.
- FIX: Add typed settings and apply them only for PostgreSQL asyncpg.
- TEST: Add engine configuration unit test if engine construction is later abstracted.
- STATUS: Fixed.

### MEDIUM: Redis FSM fallback was too silent for production

- FILE: `app/main.py`, `app/bot/factory.py`
- LOCATION: `ensure_redis_available()`, `create_dispatcher()`
- PROBLEM: Redis failures could fall back to memory storage.
- WHY: Memory FSM is acceptable in development but not in production with restarts or multiple workers.
- FIX: Production startup pings Redis when `REDIS_URL` is set and raises on failure; production does not swallow RedisStorage creation errors.
- TEST: Add mocked Redis failure test before CI hardening.
- STATUS: Fixed.

### MEDIUM: Subscription URL inserted into HTML without escaping

- FILE: `app/bot/texts.py`
- LOCATION: `connection_link()`
- PROBLEM: URL string was inserted into `<code>` without escaping.
- WHY: `SUBSCRIPTION_BASE_URL` comes from config; invalid or compromised config could break Telegram HTML markup.
- FIX: Escape URL before rendering.
- TEST: `test_connection_link_escapes_url`.
- STATUS: Fixed.

### MEDIUM: Public subscription endpoint has no rate limiting

- FILE: `app/api/routes/subscription.py`
- LOCATION: `happ_subscription()`
- PROBLEM: `/s/{token}` has token format validation but no rate limiting.
- WHY: Token brute force is infeasible with current entropy, but known-token abuse and DoS are still possible.
- FIX: Add reverse-proxy or Redis-backed rate limiting on VPS.
- TEST: Rate-limit integration test with configured backend.
- STATUS: Not fixed now. Needs deployment-level decision.

### MEDIUM: SQLite tests do not prove PostgreSQL row-lock behavior

- FILE: `tests/`
- LOCATION: service tests using SQLite
- PROBLEM: SQLite ignores or differs on `SELECT FOR UPDATE`, isolation and concurrent writers.
- WHY: Passing SQLite tests can give false confidence about PostgreSQL concurrency.
- FIX: Add PostgreSQL integration tests using Docker/service container.
- TEST: Concurrent `/start`, device add, subscription extend, payment completion against PostgreSQL.
- STATUS: Not fixed now. Requires integration test environment.

### LOW: `SECRET_KEY` is validated but not used yet

- FILE: `app/config.py`, `.env.example`
- LOCATION: `Settings.secret_key`
- PROBLEM: `SECRET_KEY` is required in production but currently unused.
- WHY: It is reserved for future signing/webhook/payment work; unused secrets can confuse operators.
- FIX: Keep validation, document that it is reserved for upcoming signed flows.
- TEST: Production config validation tests.
- STATUS: Accepted for MVP.

### LOW: No real backup/restore process

- FILE: deployment/operations
- LOCATION: outside code
- PROBLEM: Codebase cannot prove backups work.
- WHY: Paid service data requires restore drills.
- FIX: Configure VPS PostgreSQL backups and perform restore test.
- TEST: Restore a dump into disposable DB and run migrations/app smoke.
- STATUS: Not fixed in code.

## PostgreSQL vs SQLite Risk Notes

SQLite tests are useful for fast service-layer checks, but they do not prove:

- `SELECT FOR UPDATE` behavior;
- PostgreSQL lock ordering and lock waits;
- asyncpg timeout behavior;
- check constraint behavior during online migrations;
- transaction isolation under real concurrent callbacks;
- connection pool exhaustion behavior.

Before first paying customers, add PostgreSQL integration tests for:

- duplicate Telegram `/start`;
- concurrent device creation at limit;
- concurrent subscription extension;
- concurrent payment callbacks;
- duplicate future webhook callbacks.

## What Was Fixed In This Pass

- Escaped subscription link HTML rendering.
- Added production DB password validation.
- Required `ADMIN_TELEGRAM_IDS` in production.
- Required HTTPS `HAPP_DOWNLOAD_URL` in production.
- Added PostgreSQL pool settings and command timeout settings.
- Added `hide_parameters=True` to SQLAlchemy engine.
- Added Redis startup check for production.
- Removed explicit `baza:baza` compose override in favor of env interpolation.
- Updated `.env.example` with DB password and pool settings.

## What Remains

- Real VPS firewall/TLS/reverse proxy configuration.
- Secret rotation for any real values currently in local `.env`.
- PostgreSQL integration tests.
- Rate limiting for `/s/{token}`.
- Backup and restore process.
- Single-consumer bot deployment rule.
- Dependency vulnerability scanning.

## What Must Not Be Done Before VPS

- Do not add Kubernetes.
- Do not split into microservices.
- Do not add real payment provider yet.
- Do not add real VPN provider yet.
- Do not move to Telegram webhook just to appear production-grade.
- Do not add complex queues or distributed architecture before actual load requires it.

## VPS Checklist

Before VPS launch:

- Set `APP_ENV=production`.
- Set strong `SECRET_KEY`.
- Rotate and set real `BOT_TOKEN`.
- Set strong `POSTGRES_PASSWORD`.
- Set `DATABASE_URL` with the strong password.
- Set explicit `ADMIN_TELEGRAM_IDS`.
- Set HTTPS `SUBSCRIPTION_BASE_URL`.
- Set explicit `ALLOWED_HOSTS`.
- Put FastAPI behind TLS reverse proxy.
- Restrict firewall: expose only SSH, HTTP/HTTPS as needed.
- Keep PostgreSQL and Redis internal/private.
- Run `alembic upgrade head`.
- Configure backups and test restore.

## Commands Used For Verification

```powershell
python -m pytest -q
alembic upgrade head --sql
docker build -t baza-vpn:review .
python -m compileall -q app tests
```

## Production Readiness Score

Score: 72 / 100.

Reasoning:

- Architecture is clean for MVP.
- Core service boundaries are good.
- Tests are meaningful and increasing.
- Security posture is much better than the initial scaffold.
- Still missing VPS operations, PostgreSQL integration tests, rate limiting, backups, and real provider hardening.
