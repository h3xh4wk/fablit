# Practice Coverage — Activity Library Inventory (SPEC-023)

**Document ID:** PC-002
**Version:** 1.0.0
**Status:** Current
**Last Updated:** 2026-09-23

---

# Purpose

This document is the content inventory required by SPEC-023 §11 and §19: the
activities available in Fablit, the internal practice capability each one
primarily exercises, and the coverage gaps that remain.

The Observe / Interpret / Ideate / Articulate / Reflect lens below is a
**content-design and review aid only**. It is not a learner-facing taxonomy,
not a Skill hierarchy, and not a mastery model: learners never see these
labels, and nothing in the application selects, orders, or recommends
activities using them (SPEC-023 §6, §14, AC-023-12, AC-023-13).

---

# The five capabilities (internal lens)

- **Observe** — the learner notices what is actually present.
- **Interpret** — the learner asks what the observed information might mean.
- **Ideate** — the learner transforms observation or interpretation into a possibility.
- **Articulate** — the learner explains their thinking.
- **Reflect** — the learner looks back at the attempt.

---

# Activity inventory

## Original baseline (SPEC-012 / SPEC-015 / SPEC-016)

| # | Activity | Type | Stimulus | Primary capability | Secondary capabilities | Short Drill |
|---|----------|------|----------|--------------------|------------------------|-------------|
| 1 | CAT Practice — 2D & 3D Composition Analysis | Written response | Bundled image | Interpret | Observe | — |
| 2 | Creative Writing — Concept Explanations for Poster Designs | Written response | — | Articulate | — | ✔ |
| 3 | Memory Drawing Prep — Object & Proportion Detection | Observation | Bundled image | Observe | Interpret | ✔ |
| 4 | Situation Test Prep — Material & Design Process Reflection | Reflection | — | Reflect | — | — |
| 5 | Color Theory — Mood & Atmosphere Interpretation | Written response | Bundled image | Interpret | Observe, Articulate | — |

## Added by SPEC-023

| # | Activity | Type | Stimulus | Primary capability | Secondary capabilities | Short Drill |
|---|----------|------|----------|--------------------|------------------------|-------------|
| 6 | Observation Drill — Everyday Object Study | Observation | Bundled image | Observe | Interpret | ✔ |
| 7 | Visual Interpretation — Reading a Street Scene | Written response | Bundled image | Interpret | Observe, Articulate | — |
| 8 | Short Ideation Sprint — Alternative Uses | Written response | — | Ideate | Articulate | ✔ |
| 9 | Design Ideation — Transform the Object | Written response | Bundled image | Ideate | Interpret, Articulate | — |
| 10 | Composition Detective — What Holds This Together? | Observation | Bundled image | Observe | Interpret | — |
| 11 | Design Articulation — Explain a Poster Concept | Written response | — | Articulate | Ideate | ✔ |
| 12 | Reflection Prompt — What Did Practice Ask of You? | Reflection | — | Reflect | — | ✔ |

**Totals:** 12 activities · 4 image-dependent with deterministic bundled
fallbacks among the new additions (7 of 12 overall) · Short Drill set of 6.

---

# Coverage by capability

| Capability | Primary activities | Assessment |
|---|---|---|
| Observe | 3, 6, 10 | Well covered: detail detection on surfaces, everyday objects, and abstract arrangements |
| Interpret | 1, 5, 7 | Well covered: composition, colour/mood, and scene reading |
| Ideate | 8, 9 | Covered: divergent generation and grounded transformation |
| Articulate | 2, 11 | Covered: concept explanation and design-rationale explanation |
| Reflect | 4, 12 | Covered: process reflection and post-practice reflection |

Every capability has at least two primary activities, and each activity has
exactly one documented primary capability (AC-023-02, AC-023-03).

---

# Variety dimensions (§10)

| Dimension | Coverage across the library |
|---|---|
| Stimulus | Photograph-style composition, object detail, colour landscape, object study, street scene, object transformation, abstract arrangement, and seven text-first contexts |
| Thinking | Notice, compare, interpret, transform, generate, explain, reflect |
| Response | Detail description, analysis, scene reading, idea lists, design explanation, reflective response |
| Context | Visual composition, everyday objects, fashion/editorial, street scenes, poster design, personal practice process |
| Effort | 6 Short Drill activities and 12 Full Practice activities |
| Capability | All five represented as primary; secondaries distributed across 9 of 12 activities |

No two activities share a prompt; no two stimulus activities share a
retrieval query or a bundled fallback image (enforced by automated
content tests in `tests/application/test_demo_content.py`).

---

# Remaining coverage gaps (for the next iteration)

These gaps are **intentional and documented**, not oversights (§21):

1. **Three-dimensional / spatial reasoning** — no activity yet asks the
   learner to reason about objects across views or in space (the "3D" in the
   CAT exam label remains composition-focused).
2. **Human figure and gesture** — figure observation appears only as part of
   the street-scene scene reading; no focused figure-proportion or gesture
   activity exists.
3. **Material and texture ideation** — materials appear as observation
   targets (activities 3, 6), but no activity asks the learner to design
   *with* a material's properties (Situation Test-style material substitution).
4. **Colour application** — colour is observed and interpreted (activities
   5, 7) but never applied as a design decision (palette construction, colour
   planning for a poster).
5. **Sequential / narrative thinking** — storyboards, panels, and step
   sequences are absent.
6. **Sketch-adjacent warm-ups** — the library deliberately keeps sketching as
   the learner's primary offline preparation activity (§4, out of scope);
   drawing prompts that pair with a sketch could be a future family.
7. **Audio / time-based stimuli** — out of scope for the current stimulus
   architecture (still images only) and not attempted here.

The next content iteration should also re-balance Short Drill eligibility
after observing which drills learners actually repeat — through content
review, never through learner history (§8, AC-023-12).
