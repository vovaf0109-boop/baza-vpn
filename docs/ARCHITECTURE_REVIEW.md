# Architecture Review

## 1. Executive Summary

Baza VPN is currently a small modular monolith with a clear and appropriate direction for an MVP: Telegram handlers and FastAPI routes call application services, services use repositories, and repositories isolate database access. The current architecture is a good starting point and should not be replaced with microservices, Kubernetes, Celery, webhook-based Telegram delivery, real payment integrations, or real VPN integrations yet.

The most important production-readiness gaps are not product features. They are safety and correctness issues: production configuration validation, Docker hardening, concurrency protection around idempotent operations, input validation for public token endpoints, and clearer security posture documentation.

This review intentionally treats the code as pre-production. Passing tests does not mean production-ready.

## 2. Current Architecture

Current request flow:

```text
Telegram / HTTP
  -> aiogram handlers / FastAPI routes
  -> application services
  -> repositories
  -> PostgreSQL / Redis / provider abstractions
```

Main components:

- `app/main.py` creates the FastAPI app and starts aiogram polling during application lifespan.
- `app/config.py` loads typed settings from environment variables.
- `app/database.py` owns async SQLAlchemy engine and session factory.
- `app/models/` defines SQLAlchemy models.
- `app/repositories/` contains persistence operations.
- `app/services/` contains business logic.
- `app/bot/handlers/` contains Telegram UI handlers.
- `app/api/routes/` contains HTTP routes.
- `alembic/versions/` contains database migrations.
- `tests/` contains async unit-style tests with SQLite.

## 3. Architecture Strengths

- Severity: INFO
- Problem: N/A.
- Why it matters: Current separation between handlers, services, repositories, and provider stubs is suitable for a modular monolith.
- Potential impact: Positive. The project can grow without a rewrite if boundaries remain intact.
- Concrete solution: Preserve the current layering and avoid adding infrastructure before real need.
- Files affected: `app/bot/handlers/*`, `app/services/*`, `app/repositories/*`, `app/api/routes/*`.

Additional strengths:

- Telegram handlers do not execute raw SQL.
- Payment and VPN integrations are abstracted behind `PaymentProvider` and `VpnProvider`.
- Subscription tokens use `secrets.token_urlsafe(32)`, which is appropriate entropy for MVP.
- `telegram_id` is unique at PostgreSQL level via migration.
- Payment provider transaction id has a unique constraint.
- The `.env` file is ignored by Git.

## 4. Critical Issues

### CRITICAL-1: Production can start with missing critical secrets

- Severity: CRITICAL
- Problem: `BOT_TOKEN` and `SECRET_KEY` can be empty. In production, an empty bot token silently disables polling and an empty secret creates unsafe assumptions for future crypto/session use.
- Why this is a problem: Production deployments must fail fast on missing security-critical configuration.
- Potential impact: Silent broken production, weak future security guarantees, operational confusion.
- Concrete solution: Add an explicit environment mode and validate production config at startup.
- Files affected: `app/config.py`, `.env.example`, `README.md`, tests.

## 5. High Priority Issues

### HIGH-1: Payment idempotency is not protected against concurrent processing

- Severity: HIGH
- Problem: `PaymentService.complete_payment()` checks `payment.status` in Python without locking an existing pending payment row.
- Why this is a problem: Two concurrent confirmations for the same provider transaction can both observe `pending` and both activate/extend subscription.
- Potential impact: Double subscription extension when real payment callbacks are added later.
- Concrete solution: Load existing payment rows with `FOR UPDATE` in PostgreSQL before checking status.
- Files affected: `app/repositories/payment_repository.py`, `app/services/payment_service.py`, tests.

### HIGH-2: Subscription extension can race

- Severity: HIGH
- Problem: `SubscriptionService.activate()` reads and modifies `expires_at` without locking the subscription row.
- Why this is a problem: Concurrent extensions can lose updates or apply incorrectly.
- Potential impact: Wrong subscription expiry dates.
- Concrete solution: Use `FOR UPDATE` when reading subscription rows for mutation.
- Files affected: `app/repositories/subscription_repository.py`, `app/services/subscription_service.py`.

### HIGH-3: Device limit is vulnerable to TOCTOU race

- Severity: HIGH
- Problem: `DeviceService.add()` counts active devices, then inserts a new device. Concurrent requests can pass the count check before either insert commits.
- Why this is a problem: Device limit can be exceeded under concurrency.
- Potential impact: Broken tariff/device enforcement.
- Concrete solution: Lock the user row while checking and adding a device.
- Files affected: `app/repositories/user_repository.py`, `app/services/device_service.py`.

### HIGH-4: Docker container runs as root and publishes database/cache ports broadly

- Severity: HIGH
- Problem: Dockerfile runs as root. Compose publishes PostgreSQL and Redis as `5432:5432` and `6379:6379`.
- Why this is a problem: Root containers increase blast radius. Published DB/cache ports can become reachable outside the host depending on environment.
- Potential impact: Increased compromise impact and accidental exposure of infrastructure services.
- Concrete solution: Run app as non-root. Bind local development DB/cache ports to `127.0.0.1` or remove public port publishing in production.
- Files affected: `Dockerfile`, `docker-compose.yml`.

## 6. Medium Priority Issues

### MEDIUM-1: Happ subscription endpoint accepts malformed tokens

- Severity: MEDIUM
- Problem: `/s/{token}` sends any path token to DB lookup.
- Why this is a problem: Malformed tokens cause unnecessary DB work and make enumeration/noise easier.
- Potential impact: Avoidable load and noisier security monitoring.
- Concrete solution: Validate token format before DB access and return the same not-found response for invalid and missing tokens.
- Files affected: `app/api/routes/subscription.py`, `app/utils/security.py`, tests.

### MEDIUM-2: FastAPI docs remain exposed in production

- Severity: MEDIUM
- Problem: `/docs`, `/redoc`, and `/openapi.json` are always enabled.
- Why this is a problem: Public API discovery is not needed for this MVP.
- Potential impact: Increased attack surface and unnecessary information disclosure.
- Concrete solution: Disable docs/openapi automatically in production mode.
- Files affected: `app/main.py`, `app/config.py`, tests.

### MEDIUM-3: Config URLs and admin ids are weakly validated

- Severity: MEDIUM
- Problem: `HAPP_DOWNLOAD_URL`, `SUBSCRIPTION_BASE_URL`, `SUPPORT_USERNAME`, and `ADMIN_TELEGRAM_IDS` are accepted as loosely parsed strings.
- Why this is a problem: Misconfiguration can produce broken links or runtime exceptions.
- Potential impact: Broken UX or failed startup in production.
- Concrete solution: Add validators for URL scheme, username format, positive Telegram IDs, and numeric limits.
- Files affected: `app/config.py`, tests.

### MEDIUM-4: Admin extension input is unbounded

- Severity: MEDIUM
- Problem: `/extend <id> <days>` accepts any positive integer.
- Why this is a problem: A typo can create absurd expiry dates or runtime datetime errors.
- Potential impact: Operational mistake, broken subscription dates.
- Concrete solution: Add a configured maximum admin extension window and validate command input.
- Files affected: `app/config.py`, `app/bot/handlers/admin.py`, tests.

### MEDIUM-5: Blocked users can enter some business flows before later denial

- Severity: MEDIUM
- Problem: Subscription creation/activation services do not consistently reject blocked users.
- Why this is a problem: Access should be denied at business-service level, not only at UI or VPN rendering.
- Potential impact: Inconsistent state for blocked users.
- Concrete solution: Have subscription mutation methods reject blocked users unless a future explicit admin override is designed.
- Files affected: `app/services/subscription_service.py`, `app/bot/handlers/start.py`, tests.

### MEDIUM-6: Database status values are strings without DB check constraints

- Severity: MEDIUM
- Problem: Models use SQLAlchemy enums with `native_enum=False`, but hand-written migrations create plain strings with no check constraints.
- Why this is a problem: Invalid status values can be inserted outside the application.
- Potential impact: Runtime behavior gaps and harder data repair.
- Concrete solution: Add check constraints for status columns in a migration.
- Files affected: `alembic/versions/*`, models/migrations.

### MEDIUM-7: No explicit readiness endpoint

- Severity: MEDIUM
- Problem: `/health` only returns a static response and does not verify DB connectivity.
- Why this is a problem: Orchestrators and operators cannot distinguish app process alive from app ready.
- Potential impact: Serving traffic while DB is unavailable.
- Concrete solution: Add `/ready` that performs a lightweight DB query.
- Files affected: `app/api/routes/health.py`, `app/api/deps.py`, tests.

## 7. Low Priority Issues

### LOW-1: Logging is plain text, not structured JSON

- Severity: LOW
- Problem: Logs are useful but not structured.
- Why this is a problem: Later production log analysis is harder.
- Potential impact: Lower observability quality.
- Concrete solution: Keep plain logs for now; consider structured JSON after VPS logging is selected.
- Files affected: `app/utils/logging.py`.

### LOW-2: Test database differs from PostgreSQL

- Severity: LOW
- Problem: Tests use SQLite in memory.
- Why this is a problem: SQLite cannot catch PostgreSQL-specific behavior such as row locks and some constraints.
- Potential impact: Some concurrency issues only visible in integration tests.
- Concrete solution: Keep SQLite unit tests, add PostgreSQL integration tests before production.
- Files affected: `tests/`.

## 8. Security Findings

- Admin authorization is based on Telegram ID only, which is correct. It does not trust username or first name.
- The project must still harden production config validation, public token validation, Docker runtime user, and FastAPI docs exposure.
- Subscription tokens have adequate entropy, but they are bearer tokens. Logs must never include them.
- The code does not currently log full Telegram updates or subscription tokens.
- No raw SQL or command execution paths were found in request handling code.

## 9. Database Findings

- `users.telegram_id` is unique at DB level.
- `subscriptions.user_id` and `subscriptions.token` are unique at DB level.
- `payments(provider, provider_payment_id)` is unique at DB level.
- Foreign keys are present.
- Main missing integrity controls are status check constraints and row locks around concurrent mutations.

## 10. Concurrency Findings

Operations requiring idempotency or serialization:

- `/start`: mostly safe due to unique `telegram_id`; should keep savepoint handling.
- trial creation: protected by unique `subscriptions.user_id`, but blocked-user checks should happen in service.
- payment completion: needs row lock for future real callbacks.
- subscription extension: needs row lock.
- device add: needs per-user lock around count + insert.

## 11. Docker Findings

- Base image is reasonable for MVP.
- Container currently runs as root.
- PostgreSQL and Redis are published to all host interfaces.
- No app healthcheck/restart policy is configured.
- Entrypoint uses shell `CMD` without explicit signal-preserving `exec`.

## 12. Testing Findings

Existing tests cover useful domain flows:

- user creation and duplicate Telegram user;
- trial creation and one-trial rule;
- expiration/renewal;
- device limit;
- payment idempotency;
- token generation;
- inactive subscription cannot get VPN config.

Missing tests:

- production config validation;
- malformed public subscription token;
- blocked user business rules;
- admin authorization and admin input validation;
- FastAPI docs disabled in production;
- readiness endpoint;
- PostgreSQL integration/concurrency tests.

## 13. Scalability Assessment

For 300 users, the current modular monolith is enough.

For 1,000 users, the same architecture remains fine if DB indexes, connection pool configuration, and rate limiting are handled.

For 10,000 users, the monolith can still work, but the project will need real production observability, backup/restore, rate limiting at edge/proxy level, PostgreSQL integration tests, and a real deployment model.

Nothing currently justifies microservices, Kafka, Kubernetes, or Celery.

## 14. Recommended Architecture

Keep the current architecture:

```text
Telegram / HTTP
  -> handlers / routes
  -> application services
  -> repositories
  -> PostgreSQL / Redis / provider abstractions
```

Recommended additions:

- typed environment mode: development/test/production;
- service-level mutation locks where invariants depend on read-then-write;
- public input validation for token endpoints;
- explicit readiness endpoint;
- hardened Docker runtime;
- focused tests for security and concurrency safeguards.

## 15. Migration Plan

Immediate safe changes:

1. Add production config validation.
2. Add token format validation.
3. Add DB row-lock helpers in repositories.
4. Add service-level blocked-user checks.
5. Add admin input bounds.
6. Harden Dockerfile and Compose.
7. Add readiness endpoint.
8. Add tests for the above.

Later changes before production:

1. Add status check constraints migration.
2. Add PostgreSQL integration test suite for concurrency.
3. Add edge/proxy rate limiting.
4. Configure backups and monitoring.

## 16. Things NOT to change yet

- Do not move to webhook Telegram delivery yet.
- Do not add real payment providers yet.
- Do not add real VPN servers yet.
- Do not split into microservices.
- Do not add Kubernetes, Kafka, service mesh, or cloud-specific infrastructure.
- Do not add a complex admin panel before operational needs are clearer.
