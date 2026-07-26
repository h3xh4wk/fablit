# ADR-002: Choosing SQLModel

Date: 2026-07-20

## Status

Accepted

## Context

We need a Python ORM/ODM layer that combines SQLAlchemy's power with Pydantic's data validation and typing. The codebase will rely on typed models for validation at both the API boundary and persistence layer. Developer productivity and type-safety are priorities for maintainability.

## Decision

Use SQLModel (which combines Pydantic and SQLAlchemy) as the primary data modelling and persistence library.

## Consequences

- Unified models: Use the same typed models for both validation and persistence, reducing duplication.
- Developer ergonomics: Pydantic integration gives clear validation, serialization, and IDE support.
- Compatibility: Built on SQLAlchemy core, enabling access to mature SQL features and migrations tools.
- Migrations: Continue to use Alembic (via SQLAlchemy) for schema migrations; may need light glue code.
- Learning curve: Team members must be comfortable with SQLModel idioms and interplay with raw SQLAlchemy when needed.

## Alternatives Considered

- SQLAlchemy + Pydantic separately: More explicit separation but requires extra boilerplate to keep models in sync.
- Django ORM: Robust but less flexible outside Django ecosystem and not type-first.
- Tortoise ORM: Async-first but less mature and fewer integrations compared to SQLAlchemy ecosystem.

Record prepared by: Architecture Team
