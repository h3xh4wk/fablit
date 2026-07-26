# ADR-008: PythonAnywhere deployment

Date: 2026-07-20

## Status

Accepted (for initial deployment)

## Context

For initial public-facing deployment we want a simple, low-cost hosting option that supports Python web apps, allows easy domain setup, and requires minimal DevOps effort. This will serve the MVP while we validate product-market fit.

## Decision

Use PythonAnywhere for the initial deployment of the MVP, leveraging its simplicity for hosting FastAPI (via ASGI support with Uvicorn) or a WSGI-compatible adapter where needed.

## Consequences

- Low operational overhead: Quick deployment, simple scaling for low-to-moderate traffic.
- Developer productivity: Easy web-based management and consoles for debugging.
- Limitations: Less control than IaaS/PaaS providers; may require migration to a more scalable platform (e.g., Cloud Run, managed Kubernetes) as traffic grows.

## Alternatives Considered

- Heroku / Render / Fly.io: Easier scaling and more control but may increase cost and operational complexity.
- Cloud providers (AWS/GCP/Azure): Best long-term scalability and integrations but higher initial operational burden.

Record prepared by: Ops + Product
