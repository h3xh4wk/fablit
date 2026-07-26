# ADR-006: Plugin architecture for Skill Labs

Date: 2026-07-20

## Status

Proposed

## Context

The Skill Labs product expects extensibility so instructors and third parties can add new interactive exercises, scoring rules, and content types without modifying the core codebase. Plugins should be sandboxed, discoverable, and have a clearly defined API surface.

## Decision

Design a plugin architecture with the following properties:

- Lightweight plugin manifest format (YAML/JSON) describing metadata and entry points.
- Plugins implemented as Python packages or as isolated script bundles with a stable runtime API surface.
- Runtime discovery via a `plugins/` directory or Python entry points, with capability gating and signature verification for third-party plugins.
- Clear interfaces for hooks (e.g., content rendering, scoring, event handlers) and a sandboxing strategy using process isolation where needed.

## Consequences

- Extensibility: Enables third-party contributions and faster iteration on lab content and features.
- Complexity: Requires versioning, compatibility management, and a plugin API stability commitment.
- Security: Must enforce limits and sandboxing to prevent malicious or unstable plugins from affecting core services.
- Deployment: Plugin lifecycle (install/uninstall/upgrade) must be supported in deployments and CI pipelines.

## Alternatives Considered

- Monolithic features: Simpler initially but limits external contributions and slows innovation.
- Full microservice approach per plugin: Higher isolation but increases operational overhead.

Record prepared by: Product + Architecture
