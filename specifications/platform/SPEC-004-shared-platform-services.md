# SPEC-004 — Shared Platform Services

**Specification ID:** SPEC-004
**Title:** Shared Platform Services
**Version:** 0.2.0
**Status:** Implemented
**Priority:** High
**Epic:** Platform Foundation

---

# Purpose

Provide reusable platform services that can be shared across current and future Fablit modules.

These services establish common infrastructure for:

* authentication context
* configuration loading
* health checking
* correlation-aware logging
* application metrics
* resilience
* shared platform utilities

The services reduce duplication, improve consistency, and provide stable platform capabilities for future domain modules.

This specification intentionally excludes educational business logic.

---

# Background

As Fablit evolves from a platform foundation toward a learning platform, multiple modules will require common infrastructure.

Shared concerns should be implemented once at the platform level rather than independently inside Skill Labs, Assessments, or other future modules.

SPEC-004 therefore establishes reusable platform primitives while maintaining a clear boundary between platform infrastructure and educational-domain concepts.

---

# Objectives

The platform shall provide reusable services for:

* authentication helpers
* configuration loading and overrides
* health and readiness checks
* correlation-aware logging
* application metrics
* retry behaviour
* circuit breaking
* shared platform utilities

These services shall remain independent of educational-domain concepts.

---

# Scope

## In Scope

* Authentication helpers
* Bearer-token parsing
* Authentication introspection abstraction
* Configuration loading helpers
* Configuration overrides
* Health checks
* Readiness checks
* Correlation context
* Metrics registry
* Metrics rendering
* Retry utilities
* Circuit breaker
* Shared platform utilities
* Automated tests for platform services

---

## Out of Scope

* User management
* Authentication policy
* Identity-provider implementation
* Database persistence
* Business-domain authorization rules
* Skill Lab logic
* Assessment logic
* Submission processing
* Evaluation logic
* Feedback logic
* AI integrations
* Educational-domain workflows

---

# Platform Services

## Authentication

The platform provides reusable authentication helpers without implementing a complete identity-management system.

Capabilities include:

* Bearer-token parsing
* Authentication context representation
* Token introspection through an injectable client abstraction

The platform does not own user management or identity-provider policy.

---

## Configuration

The platform provides reusable configuration-loading functionality in addition to the application-level configuration model established by SPEC-003.

Configuration loading supports:

* optional configuration files
* JSON configuration
* YAML configuration
* configuration overrides
* environment-variable configuration
* validated `AppConfig` creation

Configuration remains a platform concern and does not contain educational-domain configuration.

---

## Health

The platform provides health-check primitives that allow the application to distinguish readiness and liveness concerns.

Health checking supports:

* readiness checks
* liveness checks
* aggregate health-check results
* ready/not-ready status

Health checks are intended to provide a reusable foundation for application and operational health reporting.

---

## Logging and Correlation

The platform provides reusable correlation context that can associate application activity with request and trace identifiers.

Correlation context is scoped so that request-specific values do not leak between operations.

The logging capabilities established by SPEC-003 remain the central logging mechanism for the application.

SPEC-004 provides reusable access to correlation information for platform services.

---

## Metrics

The platform provides an in-memory metrics registry for application-level counters and rendering.

The implementation supports:

* counter registration
* counter incrementing
* metrics rendering

The metrics implementation is intentionally lightweight and does not introduce an external monitoring system.

---

## Resilience

The platform provides reusable resilience primitives for operations that may fail transiently or repeatedly.

Current capabilities include:

* retry behaviour
* circuit breaking

Retry behaviour supports bounded attempts.

Circuit breaking supports failure thresholds and recovery timing.

The resilience layer is intended to provide reusable infrastructure without introducing domain-specific retry or recovery rules.

---

## Shared Utilities

The platform provides reusable utilities for common cross-cutting concerns.

Shared utilities shall remain small, focused, and independent of educational-domain behaviour.

New utilities should only be introduced when they provide genuine reuse across platform or application components.

---

# Functional Requirements

## FR-001

The platform shall provide reusable authentication helpers for bearer-token parsing.

---

## FR-002

The platform shall provide an authentication introspection abstraction that can resolve an authentication token into an authentication context.

---

## FR-003

The platform shall provide reusable configuration-loading functionality.

Configuration loading shall support configuration files, overrides, and environment-based configuration as defined by SPEC-003.

---

## FR-004

The platform shall provide health-check functionality capable of evaluating readiness and liveness.

---

## FR-005

The platform shall provide correlation context for request and trace identifiers.

Correlation context shall be isolated between operations.

---

## FR-006

The platform shall provide an in-memory metrics registry.

The registry shall support counter creation, incrementing, and rendering.

---

## FR-007

The platform shall provide a retry utility supporting bounded retry attempts.

---

## FR-008

The platform shall provide a circuit-breaker abstraction capable of transitioning to an open state after configured failures.

---

## FR-009

Platform services shall remain independent of educational-domain concepts.

---

## FR-010

Future modules shall consume shared platform services where applicable rather than duplicating equivalent infrastructure.

---

## FR-011

Shared platform services shall expose behaviour through small, reusable interfaces where abstraction is justified.

---

## FR-012

Platform services shall not require future educational modules to depend on implementation-specific infrastructure details.

---

# Non-Functional Requirements

Platform services shall be:

* modular
* reusable
* testable
* independently understandable
* minimally coupled
* framework-independent where practical
* documented
* safe to reuse across future modules

Platform services shall not introduce unnecessary infrastructure dependencies.

Platform services shall remain below the educational domain boundary.

---

# Architecture Boundary

The shared platform shall remain below the educational domain.

Conceptually:

```text
┌───────────────────────────────────────┐
│           Learning Domain             │
│                                       │
│ Learner · Skill · Skill Lab           │
│ Assessment · Submission · Feedback    │
│ Reflection · Progress                 │
└───────────────────┬───────────────────┘
                    │
                    │ consumes
                    ▼
┌───────────────────────────────────────┐
│          Shared Platform              │
│                                       │
│ Auth · Config · Health · Logging      │
│ Metrics · Resilience · Utilities      │
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│       Application / Framework         │
│                                       │
│ FastAPI · Runtime · Python            │
└───────────────────────────────────────┘
```

Educational concepts shall not be introduced into the shared platform merely because a current domain feature needs them.

---

# Implementation

The implemented shared platform services are organized as:

```text
fablit/
└── platform/
    ├── auth.py
    ├── config.py
    ├── health.py
    ├── logging.py
    ├── metrics.py
    ├── resilience.py
    └── utils.py
```

These modules provide reusable platform capabilities for the application and future modules.

---

# Application Integration

The application integrates platform capabilities for:

* configuration
* centralized logging
* request correlation
* metrics
* health status

The application exposes platform-oriented operational endpoints including:

* `/health`
* `/metrics`

These endpoints provide operational visibility without introducing educational-domain behaviour.

---

# Testing

Automated tests cover the externally observable behaviour of the shared platform services.

Testing includes:

* correlation context
* metrics counters and rendering
* configuration merging
* bearer-token parsing
* authentication introspection
* retry behaviour
* circuit-breaker behaviour
* health-check behaviour

Tests shall focus on platform behaviour rather than implementation details.

---

# Acceptance Criteria

The following criteria define completion of SPEC-004:

* [x] Authentication helpers are available for future consumers.
* [x] Bearer-token parsing is implemented and tested.
* [x] Authentication introspection is represented through a reusable abstraction.
* [x] Configuration loading and overrides are reusable.
* [x] Health checking supports readiness and liveness.
* [x] Correlation context tracks request and trace identifiers.
* [x] Correlation context is isolated between operations.
* [x] Metrics counters can be registered and incremented.
* [x] Metrics can be rendered in a machine-readable text format.
* [x] Retry behaviour is bounded and tested.
* [x] Circuit-breaker behaviour is tested.
* [x] Platform services contain no educational business logic.
* [x] Automated tests pass.
* [x] CI quality gates pass.
* [x] Documentation reflects the implemented platform structure.

---

# Relationship to Previous Specifications

SPEC-004 builds upon the configuration and logging capabilities established by SPEC-003.

SPEC-003 remains responsible for application configuration and centralized logging behaviour.

SPEC-004 provides reusable platform-level services that can consume or extend those capabilities where appropriate.

The specifications together establish the shared infrastructure required by future Fablit modules.

---

# Relationship to Future Specifications

Future domain specifications shall use these platform services where appropriate.

Future specifications shall not duplicate platform concerns such as:

* configuration loading
* correlation context
* health checking
* metrics registration
* retry behaviour
* circuit breaking
* common authentication helpers

New platform abstractions should only be introduced when justified by a concrete requirement.

A new shared service should provide demonstrable reuse across multiple components or modules rather than being introduced for speculative future needs.

Future domain specifications shall preserve the separation between platform infrastructure and educational-domain behaviour.

---

# Architectural Constraints

The shared platform shall not contain:

* Learner logic
* Skill logic
* Skill Lab logic
* Assessment logic
* Submission logic
* Evaluation rules
* Feedback logic
* Reflection logic
* Progress logic
* educational-domain business rules

Platform services shall remain reusable without requiring knowledge of the educational domain.

---

# Definition of Done

SPEC-004 is considered complete when:

* Shared platform services are implemented.
* Authentication helpers are implemented.
* Configuration helpers are implemented.
* Health checks are implemented.
* Correlation context is implemented.
* Metrics registry is implemented.
* Resilience primitives are implemented.
* Shared utilities are implemented.
* Automated tests pass.
* CI quality gates pass.
* Documentation is aligned with the implementation.
* No educational-domain business logic has been introduced into the platform layer.
* Future modules can consume the shared services without duplicating equivalent platform functionality.