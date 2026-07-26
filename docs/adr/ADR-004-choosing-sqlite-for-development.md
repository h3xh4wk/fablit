# ADR-004: Choosing SQLite for development

Date: 2026-07-20

## Status

Accepted

## Context

Developers require a zero-config, fast local database that enables easy onboarding, quick tests, and simple CI matrix entries. The production DB will be PostgreSQL; we need a development database that is lightweight and reliable for local work and automated tests.

## Decision

Use SQLite as the default local development and lightweight testing database.

## Consequences

- Ease of setup: No separate DB server required; quick onboarding.
- Deterministic migrations: Fast schema changes and local runs.
- Limitations: SQLite differs from PostgreSQL in concurrency, SQL dialect, and certain features (e.g., full-text search, transactional DDL). Tests must account for these differences.
- Migration strategy: Use migrations against PostgreSQL-compatible schemas and run integration tests against PostgreSQL in CI to catch compatibility issues early.

## Alternatives Considered

- Local PostgreSQL: Closer to production but adds complexity to developer setup and resource usage.
- Dockerized PostgreSQL for dev: Good parity but higher onboarding cost.

Record prepared by: Development Lead
