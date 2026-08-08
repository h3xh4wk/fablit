# SPEC-003 — Configuration & Logging

**Specification ID:** SPEC-003
**Title:** Configuration & Logging
**Version:** 0.2.0
**Status:** Implemented
**Priority:** High
**Epic:** Platform Foundation

---

# Purpose

Provide a centralized configuration and logging framework that enables the Fablit platform to operate consistently across development, testing, staging, and production environments.

This specification establishes:

* a validated application configuration model
* environment-based configuration
* optional file-based configuration
* configuration override support
* centralized logging
* structured logging
* request correlation context
* consistent application lifecycle and request logging

The implementation provides these capabilities as reusable platform infrastructure without introducing educational-domain logic.

---

# Background

As the platform grows, configuration and logging behaviour must remain consistent across environments and modules.

Fablit therefore treats configuration and logging as platform concerns rather than allowing individual modules to implement their own approaches.

Application configuration is represented by a validated `AppConfig` model.

Configuration can be resolved from supported configuration sources, including environment variables and optional JSON or YAML configuration files.

Logging is initialized centrally and supports request-level correlation information so that application activity can be associated with a specific request or trace.

---

# Objectives

The platform shall:

* provide a single validated application configuration model
* load configuration from environment variables
* support optional JSON configuration files
* support optional YAML configuration files
* support configuration overrides
* validate configuration at application startup
* support development, testing, and production environments
* provide structured logging
* support configurable log levels
* support configurable log formats
* establish request correlation context
* support trace correlation when available
* log application startup and shutdown events
* log incoming HTTP requests
* log unexpected application exceptions
* avoid hard-coded environment-specific configuration
* simplify debugging and operational diagnosis

---

# Scope

## In Scope

* Application settings
* Configuration validation
* Environment variable management
* Configuration file loading
* JSON configuration
* YAML configuration
* Configuration overrides
* Runtime environment selection
* Logging initialization
* Log levels
* Log formats
* Request correlation
* Trace correlation
* Application startup logging
* Application shutdown logging
* HTTP request logging

---

## Out of Scope

* Monitoring systems
* Metrics collection
* Distributed tracing infrastructure
* Authentication policy
* User management
* Database configuration
* Educational-domain configuration
* Feature-specific configuration
* External secret-management infrastructure

---

# Configuration

## Configuration Model

Application configuration is represented by the `AppConfig` model.

The configuration model validates supported configuration values and prevents unsupported configuration fields from being silently accepted.

The implemented configuration includes:

* Service Name
* Environment
* Host
* Port
* Debug Mode
* Log Level
* Log Format
* Configuration File
* Application Version

---

## Supported Environments

The platform supports:

* Development
* Testing
* Production

Environment values are normalized before validation.

Unsupported environment values shall be rejected.

---

## Supported Log Formats

The platform supports:

* JSON
* Text

Log format values are normalized before validation.

Unsupported log formats shall be rejected.

---

# Configuration Sources

Configuration may be resolved from multiple supported sources.

## Environment Variables

Environment variables use the `FABLIT_` prefix.

Examples include:

```text
FABLIT_SERVICE_NAME
FABLIT_ENV
FABLIT_HOST
FABLIT_PORT
FABLIT_DEBUG
FABLIT_LOG_LEVEL
FABLIT_LOG_FORMAT
FABLIT_VERSION
FABLIT_CONFIG
```

Environment variables provide environment-specific configuration without requiring source-code changes.

---

## Configuration Files

The platform supports the following configuration file formats:

* JSON (`.json`)
* YAML (`.yaml`)
* YAML (`.yml`)

A configuration file may be specified through the `FABLIT_CONFIG` setting.

Unsupported configuration file formats shall result in a configuration error.

Missing explicitly configured files shall result in a configuration error rather than being silently ignored.

---

## Configuration Overrides

The platform supports programmatic configuration overrides.

Overrides allow callers to replace selected configuration values without modifying the underlying configuration source.

Configuration resolution follows the precedence defined by the implementation, with environment-specific configuration taking precedence where applicable.

---

# Functional Requirements

## FR-001

Application configuration shall be represented by a validated Pydantic Settings model.

---

## FR-002

The configuration model shall provide the following application settings:

* Service Name
* Environment
* Host
* Port
* Debug Mode
* Log Level
* Log Format
* Configuration File
* Version

---

## FR-003

The platform shall validate configuration values before the application successfully starts.

Invalid configuration shall prevent successful configuration creation and application startup.

---

## FR-004

The platform shall support the following runtime environments:

* Development
* Testing
* Production

Unsupported environments shall be rejected.

---

## FR-005

The platform shall support the following log formats:

* JSON
* Text

Unsupported log formats shall be rejected.

---

## FR-006

The platform shall support the following logging levels:

* DEBUG
* INFO
* WARNING
* ERROR
* CRITICAL

---

## FR-007

The platform shall initialize logging centrally during application startup.

---

## FR-008

Application startup and shutdown events shall be logged.

---

## FR-009

Incoming HTTP requests shall establish request correlation context.

The correlation context shall support:

* Request ID
* Trace ID when supplied by the caller

If no request ID is supplied, the application shall generate one.

---

## FR-010

Completed HTTP requests shall be logged with relevant request and response information, including:

* HTTP method
* Request path
* HTTP status code
* Request correlation information

Client information may be included when available.

---

## FR-011

Unexpected application exceptions shall be logged through the centralized logging infrastructure.

---

## FR-012

Configuration shall support environment-specific operation without requiring source-code modification for normal configuration changes.

---

## FR-013

Configuration and logging functionality shall remain independent of educational-domain concepts.

---

# Logging

## Centralized Initialization

Logging shall be initialized through the platform logging implementation rather than independently by individual modules.

This provides a consistent logging configuration across the application.

---

## Structured Logging

The platform supports structured logging suitable for machine-readable production output.

Human-readable text logging is also supported for development and diagnostic use.

---

## Correlation Context

The platform provides request-level correlation context.

The context may contain:

* Request ID
* Trace ID

Correlation values can be accessed by logging components during the lifetime of the associated operation.

Correlation context shall be isolated between operations to prevent request-specific values from leaking into unrelated requests.

---

# Non-Functional Requirements

The configuration and logging implementation shall be:

* centralized
* validated
* reusable
* testable
* environment-independent
* structured
* minimally duplicated

The implementation shall avoid unnecessary configuration duplication.

The implementation shall not introduce dependencies on educational-domain modules.

---

# Acceptance Criteria

The following criteria define completion of SPEC-003:

* [x] Configuration loads successfully with supported defaults.
* [x] Environment variables can override configuration values.
* [x] JSON configuration files are supported.
* [x] YAML configuration files are supported.
* [x] Configuration overrides are supported.
* [x] Invalid configuration prevents successful configuration creation.
* [x] Unsupported environments are rejected.
* [x] Unsupported log formats are rejected.
* [x] Logging can be initialized from application configuration.
* [x] Application startup is logged.
* [x] Application shutdown is logged.
* [x] HTTP requests establish correlation context.
* [x] Request IDs are accepted from incoming requests.
* [x] Missing request IDs are generated.
* [x] Trace IDs can be propagated through request context.
* [x] Completed HTTP requests are logged.
* [x] Unexpected exceptions are logged.
* [x] Configuration and logging behaviour are covered by automated tests.
* [x] Documentation reflects the implemented configuration and logging architecture.

---

# Implementation

The implemented configuration and logging functionality is organized around the following platform components:

```text
fablit/
├── config.py
└── platform/
    ├── config.py
    └── logging.py
```

The application entry point initializes configuration and logging before serving requests.

The application-level configuration model provides validated application settings.

The platform configuration layer provides reusable configuration-loading functionality.

The platform logging layer provides centralized logging and correlation-aware logging behaviour.

---

# Testing

Automated tests cover the externally observable behaviour of the configuration and logging components.

Testing includes:

* configuration defaults
* environment variable overrides
* configuration validation
* configuration file loading
* JSON configuration
* YAML configuration
* configuration overrides
* environment selection
* log-level handling
* log-format handling
* request correlation
* trace correlation
* request logging
* application lifecycle logging

Tests shall focus on observable behaviour rather than implementation details.

---

# Relationship to Other Specifications

SPEC-003 establishes the configuration and logging capabilities used by subsequent platform services.

SPEC-004 builds upon these capabilities by providing additional reusable platform services, including health checking, metrics, authentication helpers, and resilience primitives.

Future domain modules shall consume these platform capabilities rather than implement independent configuration or logging mechanisms.

---

# Architectural Constraints

Configuration and logging are platform concerns.

They shall not contain:

* Skill Lab logic
* Assessment logic
* Learner workflows
* Evaluation rules
* Feedback logic
* educational-domain business rules

The implementation shall remain usable by future modules without requiring those modules to understand platform implementation details.

---

# Definition of Done

SPEC-003 is considered complete when:

* Configuration validation is implemented.
* Environment-based configuration is implemented.
* JSON configuration support is implemented.
* YAML configuration support is implemented.
* Configuration override support is implemented.
* Centralized logging is implemented.
* Request correlation is implemented.
* Startup and shutdown logging are implemented.
* HTTP request logging is implemented.
* Automated tests pass.
* CI quality gates pass.
* Documentation is aligned with the implementation.
* No educational-domain business logic has been introduced into the configuration or logging layer.
