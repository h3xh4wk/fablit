# ADR-007: GitHub Actions CI/CD

Date: 2026-07-20

## Status

Accepted

## Context

We need an integrated CI/CD solution that ties to our GitHub-hosted repository, supports multiple job types (lint, unit tests, integration tests, migrations, deploy), and can run matrix builds for Python versions and database backends.

## Decision

Use GitHub Actions for CI/CD pipelines, including PR checks, scheduled jobs, and deployment workflows.

## Consequences

- Tight integration: Actions run close to the repo and provide standard triggers (push, PR, schedule).
- Extensible: Marketplace actions and reusable workflows speed development.
- Cost considerations: GitHub-hosted runners have limits; self-hosted runners are an option for heavy workloads.
- Security: Use secrets and fine-grained permissions; review third-party action security.

## Alternatives Considered

- CircleCI / TravisCI: Mature CI providers but add another external service and integration overhead.
- Self-hosted Jenkins: Very flexible but high operational cost and maintenance burden.

Record prepared by: DevOps Team
