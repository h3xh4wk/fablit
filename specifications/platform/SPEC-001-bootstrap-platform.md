# SPEC-001 — Bootstrap Platform

**Specification ID:** SPEC-001
**Title:** Bootstrap Platform
**Version:** 0.1.0
**Status:** Approved
**Priority:** High
**Epic:** Platform Foundation

---

# Purpose

Establish the first runnable version of the Fablit platform.

This specification defines the minimum application required to validate the architecture, engineering workflow, deployment pipeline, and local development experience.

No educational functionality shall be implemented in this specification.

---

# Objectives

The platform shall:

- start successfully
- expose a homepage
- expose a health endpoint
- expose OpenAPI documentation
- support local development
- support automated testing
- support deployment to PythonAnywhere

---

# Scope

## In Scope

- FastAPI application
- application entry point
- homepage
- health endpoint
- OpenAPI documentation
- project configuration
- automated tests
- GitHub Actions integration

---

## Out of Scope

- Authentication
- Database
- User management
- Skill Labs
- Assessments
- AI services
- Analytics
- Content Packs

---

# Functional Requirements

## FR-001

The application shall start with a single command.

---

## FR-002

The platform shall expose:

GET /

Response:

```
Welcome to Fablit
```

---

## FR-003

The platform shall expose:

GET /health

Response

```json
{
  "status": "healthy"
}
```

---

## FR-004

The application shall expose:

- /docs
- /redoc

---

## FR-005

Application startup and shutdown events shall complete successfully.

---

# Non-Functional Requirements

- Python 3.12+
- FastAPI
- uv
- Ruff
- mypy
- pytest
- Playwright
- GitHub Actions

---

# Acceptance Criteria

- Application starts
- Homepage accessible
- Health endpoint returns HTTP 200
- OpenAPI available
- Tests pass
- CI passes
- Deployable to PythonAnywhere

---

# Deliverables

- FastAPI application
- Basic routing
- Health endpoint
- Homepage
- Test suite
- CI pipeline
- Updated README

---

# Definition of Done

- Functional requirements satisfied
- Tests passing
- Documentation updated
- CI successful
- Code merged
