# Pilot Feedback Record (SPEC-014 §35)

A lightweight, structured way to record what happens during the pilot. One
record per observation. Keep entries short — this is a working document, not a
report.

## Record format

| Field | Guidance |
| --- | --- |
| **Date** | When the observation happened |
| **Learner identifier** | Minimal and non-sensitive (e.g. `L1`, `L2`) — never real names |
| **Context** | Where in the journey (dashboard, activity choice, practice, feedback, reflection, completion) |
| **Observed behaviour** | What the learner actually did — not what you think it meant |
| **Learner statement** | What the learner said, quoted where possible |
| **Potential interpretation** | Your best guess at what it meant — clearly separated from the behaviour |
| **Confidence** | Low / Medium / High |
| **Possible product implication** | A candidate change, if any — not a commitment |

## Example record

```text
Date: 2026-08-16
Learner identifier: L1
Context: Dashboard
Observed behaviour: Remained on the dashboard for ~1 minute; read multiple
  activity cards but did not select one.
Learner statement: (none — observed)
Potential interpretation: The activity invitations may not communicate enough
  curiosity to start.
Confidence: Medium
Possible product implication: Review activity-card language and visual
  hierarchy.
```

## Suggested questions to ask learners (§32)

Ask openly, and never lead the answer (§34). Avoid questions that imply the
desired answer — e.g. prefer *"What did you think about the feedback?"* over
*"Did you like the friendly feedback?"*.

- Before starting: *What do you think you can do here?*
- After choosing an activity: *What made you choose this one?*
- During practice: *Was it clear what you were being asked to do?*
- After feedback: *Did the feedback help you understand something?*
- After completion: *How did completing the activity feel?*
- End of session: *Would you try another activity? Why or why not?*

## Turning observations into findings (§36)

When a pattern emerges, write it up as a structured finding:

```text
Observation
    ↓
Evidence
    ↓
Interpretation
    ↓
Potential product implication
```

Always distinguish observed behaviour from interpretation, and remember that a
single learner request does not automatically become a feature (§37). First
ask: Is this an isolated request? Is it repeated? Does it conflict with
existing principles? Is the underlying problem understood? Is the requested
feature actually the best solution?
