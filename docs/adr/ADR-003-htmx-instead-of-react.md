# ADR-003: Choosing HTMX instead of React for MVP

Date: 2026-07-20

## Status

Accepted (for MVP)

## Context

For the initial MVP we need a frontend approach that minimizes engineering overhead, speeds iteration, simplifies deployment, and leverages server-side templates while still enabling rich interactivity. The team is small and the product prioritizes rapid experimentation over a full single-page application architecture.

## Decision

Adopt HTMX for the MVP layer to progressively enhance server-rendered pages with minimal JavaScript, deferring a React-based SPA only if future product requirements demand it.

## Consequences

- Faster iteration: Use existing server endpoints to drive UI with small HTML fragments.
- Simpler stack: Fewer build steps, no heavy JS bundling or complex client-side state management.
- SEO and accessibility: Server-rendered content improves SEO and baseline accessibility.
- Limits: For highly interactive, large-scale client-side applications, HTMX can become cumbersome; may require migration to React or another SPA later.
- Team skills: Lower frontend engineering burden; backend developers can implement much of the UI behavior.

## Alternatives Considered

- React (CRA/Vite): Powerful for complex client apps but increases complexity, tooling, and time-to-market for the MVP.
- Alpine.js: Lightweight progressive enhancement library; complements HTMX but by itself doesn't cover server-driven interactions as cleanly.
- SvelteKit: Good DX but still introduces SPA-style abstractions and build pipeline complexity.

Record prepared by: Product + Architecture
