# ADR-005: Choosing PostgreSQL for production

Date: 2026-07-20

## Status

Accepted

## Context

Production workloads require a reliable, scalable relational database with strong SQL feature support, transactional integrity, and ecosystem tooling. We expect growth in data volume and may rely on advanced features such as JSONB, indexing, and robust concurrency control.

## Decision

Use PostgreSQL as the production database.

## Consequences

- Reliability and features: PostgreSQL provides strong ACID guarantees, advanced indexing, JSONB, and extensibility.
- Operational needs: Requires managed hosting (e.g., RDS, Cloud SQL) or dedicated servers and proper backup/restore, monitoring, and scaling strategies.
- Migrations and compatibility: Ensure migration workflows and testing catch SQLite vs PostgreSQL differences; run integration tests against PostgreSQL in CI.

## Alternatives Considered

- MySQL/MariaDB: Widely used but less feature-rich for JSON operations and some PostgreSQL-specific extensions.
- Managed NoSQL (e.g., DynamoDB): Not suitable for relational transactional workloads and complex queries.

Record prepared by: Architecture Team
