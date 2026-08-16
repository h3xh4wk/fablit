# Static assets

## css/fablit.css

The Fablit learner-experience stylesheet (SPEC-013). Contains the centralized
design tokens (typography, spacing, colours, border radius, shadows,
transitions, container widths) and the small design-system primitives (page
container, type hierarchy, buttons, links, cards, forms, field errors,
feedback sections, completion messages). Served from `app/templates/base.html`.

## favicon.svg

The Fablit brand mark for the browser tab (an "F" on the design-system accent
colour). Declared in `app/templates/base.html` so browsers stop requesting a
non-existent `/favicon.ico`.

## htmx.min.js

Vendored for offline, deterministic development and tests (SPEC-012 §25).

- Library: htmx.org
- Version: 2.0.10
- Source: `https://cdn.jsdelivr.net/npm/htmx.org@2.0.10/dist/htmx.min.js`
