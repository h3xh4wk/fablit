# Fablit Learner Pilot (SPEC-014)

The pilot puts the current Fablit learner experience in front of a small group
of real learners (about 5–10) so the team can observe, learn, and improve from
actual usage instead of assumptions.

The pilot is **pilot-ready, not production-ready** (§39). It is deliberately
small: no public launch, no production-scale infrastructure, and no production
SLA.

## What we are validating

A real learner should be able to complete the full journey without developer
assistance (§47):

```text
Open Fablit → Explore activities → Choose an activity → Practise
→ Receive feedback → Reflect → Complete → Continue exploring
```

## How to run the pilot

1. Deploy per [docs/engineering/deployment.md](../engineering/deployment.md).
2. Verify the deployed experience against the public URL (browser, mobile,
   accessibility).
3. Invite learners with only the URL and the one-line instruction in
   [learner-instructions.md](learner-instructions.md).
4. Observe and record what happens using
   [feedback-record.md](feedback-record.md).
5. Run the evidence-driven loop below.

## The evidence-driven loop (§38)

```text
Deploy
   ↓
Observe
   ↓
Collect feedback
   ↓
Identify patterns
   ↓
Form findings
   ↓
Discuss implications
   ↓
Define next specification
```

This loop replaces assumption-driven feature expansion with evidence-driven
development. A learner request during the pilot does not automatically become
a feature (§37) — patterns and findings come first.

## Observation principles

- Treat *"What am I supposed to do here?"* as evidence, not as a request to
  explain (§31).
- Prioritise qualitative feedback over quantitative metrics (§32).
- Pay attention to: discoverability, curiosity, clarity, comfort, feedback,
  reflection, accomplishment, and continuation (§33).
- Never lead the learner — ask open questions (§34).
- Distinguish observed behaviour from interpretation (§36).
