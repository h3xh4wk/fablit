Absolutely. I think **SPEC-014 should be deliberately operational rather than feature-heavy**. Its job is simply to get the current Fablit experience into the hands of a small number of real learners safely and reliably.

Here is the complete specification.

````markdown
# SPEC-014 — Learner Pilot Deployment

**Specification ID:** SPEC-014
**Title:** Learner Pilot Deployment
**Version:** 0.1.0
**Status:** Draft
**Priority:** High
**Epic:** Learner Validation

---

## 1. Purpose

SPEC-014 establishes the minimum deployment and operational foundation required to place the current Fablit learner experience in front of a small group of real learners.

SPEC-013 established the first coherent learner-facing experience.

The next objective is not to add another learning capability.

The objective is:

> **Make the current Fablit experience accessible to real learners so that we can observe, learn, and improve from actual usage.**

This specification therefore focuses on pilot deployment rather than product expansion.

---

# 2. Product Intent

Fablit has reached the point where assumptions about the learner experience should begin to be replaced by evidence.

The pilot should allow learners to independently:

```text
Open Fablit
    ↓
Explore activities
    ↓
Choose an activity
    ↓
Practise
    ↓
Receive feedback
    ↓
Reflect
    ↓
Complete
    ↓
Continue exploring
````

The pilot is successful when real learners can complete this journey without requiring developer assistance.

---

# 3. Pilot Philosophy

The pilot is intentionally small.

It is not a public launch.

It is not production-scale infrastructure.

It is not intended to validate every future Fablit capability.

The pilot exists to answer:

> **Does the current Fablit experience work for real learners?**

---

# 4. Pilot Scope

The initial pilot should support approximately:

**5–10 learners.**

This is a target range rather than a hard infrastructure limit.

The deployment should be sufficient for a small number of concurrent or near-concurrent learners using the application.

The system does not need to be designed for large-scale traffic.

---

# 5. Pilot Goals

The pilot should allow the team to learn:

1. Can a learner open Fablit without assistance?
2. Do learners understand what they can do from the dashboard?
3. Do learners find an activity interesting enough to start?
4. Is the practice experience understandable?
5. Can learners submit a response successfully?
6. Does the feedback feel useful?
7. Does the feedback feel encouraging rather than judgmental?
8. Does reflection feel purposeful?
9. Does completion create a sense of accomplishment?
10. Do learners voluntarily try another activity?
11. Where do learners become confused or hesitant?

---

# 6. Explicit Non-Goals

SPEC-014 does not introduce:

* a public launch;
* production-scale infrastructure;
* payment functionality;
* subscriptions;
* multi-tenant architecture;
* recommendation systems;
* AI evaluation;
* advanced analytics;
* learner rankings;
* gamification;
* scoring;
* social features;
* instructor dashboards;
* institutional administration;
* a full authentication system unless required by the chosen deployment environment;
* a mobile application.

These may be considered later based on evidence.

---

# 7. Deployment Principle

The deployment should follow:

> **Deploy what we have. Do not redesign what we have just because we are deploying it.**

SPEC-013 is the learner experience being validated.

Deployment work should avoid introducing unnecessary product changes.

---

# 8. Environment

The pilot shall have a dedicated deployment environment separate from local development.

At minimum:

```text
Local Development
        ↓
Pilot Environment
```

The pilot environment shall be reproducible from the repository.

Environment-specific configuration shall not be hard-coded into the application.

---

# 9. Deployment Target

The implementation team may choose an appropriate hosting provider.

The exact provider is an implementation decision.

The selected environment shall provide:

* a stable publicly reachable URL;
* application process execution;
* required Python/runtime dependencies;
* persistent storage where required by the current application;
* HTTPS;
* environment configuration;
* basic logs.

The deployment provider should be inexpensive and appropriate for a small pilot.

---

# 10. Stable URL

The pilot shall have a stable URL that can be shared with learners.

The URL should:

* use HTTPS;
* remain stable during the pilot;
* not expose development infrastructure;
* not require learners to understand deployment details.

The URL should provide direct access to the Fablit learner experience.

---

# 11. Application Startup

The deployed application shall have a documented startup mechanism.

The startup command shall be:

* deterministic;
* documented;
* compatible with the selected hosting environment;
* suitable for the application's current architecture.

The deployment shall not require a developer to manually start a local process after every restart.

---

# 12. Configuration

Deployment configuration shall use environment variables or equivalent environment-specific configuration.

Examples may include:

```text
Application environment
Database/storage location
Host configuration
Port configuration
Secret configuration
Logging configuration
```

Secrets shall not be committed to the repository.

---

# 13. Secrets

No credentials, private keys, API keys, or deployment secrets shall be stored in source control.

The repository shall remain safe to clone publicly or internally without exposing deployment credentials.

If secrets are required by the deployment environment, they shall be configured through the hosting provider's secret/environment configuration mechanism.

---

# 14. HTTPS

The pilot environment shall use HTTPS.

Learners should never be asked to use an insecure HTTP connection for normal pilot access.

The implementation should use the hosting provider's managed TLS capability where available.

---

# 15. Persistence

The deployment shall preserve the persistence requirements of the current Fablit application.

At minimum, the pilot must support the current learner journey without losing required state unexpectedly during normal application operation.

The implementation team shall document:

* what data is persisted;
* where it is persisted;
* how long it is expected to survive;
* what happens when the application restarts.

If the current implementation uses lightweight in-process or local persistence, the deployment team shall explicitly verify whether that behaviour is acceptable for the pilot.

A persistence upgrade should only be introduced if the pilot requires it.

---

# 16. Pilot Data

The pilot shall use the existing demo activities and evaluation behaviour from SPEC-012 and SPEC-013.

The deployment does not require a new content-generation pipeline.

Learners should be able to use the existing activities immediately after opening the application.

---

# 17. Learner Access

The pilot should minimize friction for learners.

A learner should ideally be able to:

```text
Receive URL
    ↓
Open browser
    ↓
See Fablit
    ↓
Start exploring
```

The learner should not need:

* developer instructions;
* command-line access;
* local installation;
* Python;
* Git;
* environment configuration.

---

# 18. Authentication

Authentication is not required by default for the initial pilot.

If the selected deployment environment requires access protection, the implementation may introduce the smallest appropriate mechanism.

Any authentication introduced solely for deployment must not become a new domain concept.

The pilot should remain simple.

---

# 19. Pilot Safety Boundary

The deployment must clearly distinguish pilot functionality from production functionality.

The pilot shall not expose:

* administrative endpoints;
* development tools;
* debugging interfaces;
* source-code repositories;
* environment secrets;
* internal service credentials.

Debug output intended only for developers should not be visible to learners.

---

# 20. Error Handling

The deployed application shall provide a reasonable learner-facing experience when an unexpected error occurs.

The learner should not see:

* stack traces;
* internal file paths;
* environment variables;
* credentials;
* framework debugging pages.

A simple error page is sufficient.

For example:

```text
Something went wrong.

We couldn't complete that action.
Please try again.
```

The implementation may provide more useful information where appropriate.

---

# 21. Logging

The pilot environment shall provide basic application logs sufficient to investigate failures.

Logs should allow the team to determine:

* when the application started;
* when significant errors occurred;
* which endpoint or operation failed;
* whether the application became unavailable.

Logs shall not unnecessarily expose sensitive learner information.

---

# 22. Health Check

The deployed application should provide a simple mechanism for determining whether the application is available.

A health endpoint may be introduced if useful.

The health mechanism should remain operationally simple.

Example:

```text
GET /health
```

Expected result:

```text
200 OK
```

The exact endpoint is an implementation decision.

---

# 23. Deployment Verification

After deployment, the team shall verify the application through the actual public URL.

Verification shall include:

```text
Open dashboard
    ↓
Open activity
    ↓
Submit response
    ↓
Receive feedback
    ↓
Reflect
    ↓
Complete
    ↓
Return to practice
```

This must be tested against the deployed environment rather than only the local development server.

---

# 24. Browser Verification

The deployment verification shall use a real browser.

The team shall verify at minimum:

* dashboard rendering;
* activity selection;
* response entry;
* submission;
* feedback;
* reflection;
* completion;
* return navigation.

The existing Playwright journey from SPEC-012/SPEC-013 should remain the primary automated regression path.

---

# 25. Mobile Verification

The deployed experience shall be checked on a mobile-sized viewport.

At minimum:

* dashboard;
* activity;
* response;
* feedback;
* completion

should remain usable.

The existing SPEC-013 mobile browser test should continue to pass.

---

# 26. Accessibility Verification

The deployed experience shall preserve the accessibility behaviour introduced in SPEC-013.

At minimum:

* keyboard navigation;
* visible focus;
* accessible labels;
* semantic headings;
* skip navigation;
* readable contrast

shall remain functional.

Deployment must not introduce accessibility regressions.

---

# 27. Performance Expectations

The pilot does not require production-scale performance engineering.

However:

* the dashboard should load within a reasonable period;
* activity pages should respond normally;
* form submission should not appear unnecessarily slow;
* navigation should not contain avoidable delays.

The goal is a comfortable pilot experience, not benchmark optimization.

---

# 28. Availability Expectations

The pilot should remain available during the agreed learner testing period.

No formal production SLA is required.

If downtime occurs, the team should be able to identify and recover from it without rebuilding the application manually.

---

# 29. Backup and Recovery

A formal disaster-recovery system is outside the scope of the pilot.

However, the team shall understand:

* what learner data can be lost;
* what deployment events can reset data;
* whether the current persistence mechanism survives restart;
* how to restore the pilot environment.

The expected risk shall be documented.

---

# 30. Learner Instructions

The pilot shall provide learners with a very small amount of guidance.

The preferred instruction is intentionally simple.

For example:

> **Open Fablit and explore. Choose any activity that catches your interest, complete it, and tell us what you think.**

Learners should not receive detailed instructions about:

* where to click;
* what they are expected to say;
* how the feedback works;
* which activity to choose.

The pilot is partly intended to observe whether the interface communicates these things naturally.

---

# 31. Observation Principle

During the pilot, the team should avoid immediately explaining confusing interface elements.

If a learner asks:

> "What am I supposed to do here?"

that should first be treated as evidence.

The team may assist where necessary, but the interaction should be recorded as learner feedback.

---

# 32. Qualitative Feedback

The initial pilot should prioritize qualitative feedback over quantitative metrics.

Learners should be asked questions such as:

### Before starting

> What do you think you can do here?

### After choosing an activity

> What made you choose this one?

### During practice

> Was it clear what you were being asked to do?

### After feedback

> Did the feedback help you understand something?

### After completion

> How did completing the activity feel?

### End of session

> Would you try another activity? Why or why not?

---

# 33. Observation Areas

The team should pay particular attention to:

### Discoverability

Can learners understand what is available?

### Curiosity

Do activities appear interesting enough to start?

### Clarity

Do learners understand what each activity asks?

### Comfort

Does the practice experience feel comfortable?

### Feedback

Does feedback feel useful rather than judgmental?

### Reflection

Does reflection feel meaningful?

### Accomplishment

Does completion feel satisfying?

### Continuation

Do learners naturally want to explore another activity?

---

# 34. Avoid Leading the Learner

The team should avoid asking questions that imply the desired answer.

Avoid:

> "Did you like the friendly feedback?"

Prefer:

> "What did you think about the feedback?"

Avoid:

> "Did the activity feel fun?"

Prefer:

> "How did the activity feel?"

The purpose is to learn what learners actually experience.

---

# 35. Pilot Feedback Record

Pilot observations should be recorded in a lightweight structured format.

Each observation should ideally capture:

```text
Date
Learner identifier
Context
Observed behaviour
Learner statement
Potential interpretation
Confidence
Possible product implication
```

The learner identifier should be minimal and non-sensitive.

---

# 36. Structured Finding for Product Feedback

Where appropriate, pilot observations may eventually be turned into structured product findings.

A useful structure is:

```text
Observation
    ↓
Evidence
    ↓
Interpretation
    ↓
Potential product implication
```

The team should distinguish observed behaviour from interpretation.

Example:

```text
Observation:
Learner remained on the dashboard for approximately one minute.

Evidence:
Learner read multiple activity cards but did not select one.

Interpretation:
The activity invitations may not communicate enough curiosity.

Potential implication:
Review activity card language and visual hierarchy.
```

This prevents assumptions from immediately becoming requirements.

---

# 37. No Immediate Feature Expansion

A learner request during the pilot shall not automatically become a feature.

The team should first determine:

* Is this an isolated request?
* Is the problem repeated?
* Does it conflict with existing principles?
* Is the underlying problem understood?
* Is the requested feature actually the best solution?

The pilot exists to discover problems, not to turn every comment into scope.

---

# 38. Pilot Feedback Loop

The intended product loop becomes:

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

This replaces assumption-driven feature expansion with evidence-driven development.

---

# 39. Production Readiness Boundary

SPEC-014 does not declare Fablit production-ready.

At the end of this specification, Fablit should be:

> **Pilot-ready**

not:

> **Production-ready**

Production readiness will require a separate assessment.

Potential future areas include:

* authentication;
* authorization;
* data privacy;
* backups;
* monitoring;
* security hardening;
* scalability;
* formal analytics;
* content management;
* operational support.

These remain outside this specification.

---

# 40. Deployment Documentation

The repository shall document:

1. deployment target;
2. required runtime;
3. required environment variables;
4. build/install process;
5. startup command;
6. persistence behaviour;
7. health check;
8. log access;
9. restart procedure;
10. known pilot limitations.

The documentation should be sufficient for another developer to understand how the pilot environment operates.

---

# 41. CI/CD

A fully automated deployment pipeline is not required.

However, the deployment process should be reproducible.

If the chosen hosting provider supports straightforward deployment from GitHub, that approach is preferred.

The implementation should avoid manual modifications to the deployed application that cannot be reproduced from the repository.

---

# 42. Rollback

The team shall have a simple way to return to the last known-good pilot version.

This may be provided through:

* deployment version history;
* Git commits;
* hosting-provider rollback;
* container/image versioning.

The exact mechanism is an implementation decision.

---

# 43. Security Baseline

The pilot shall at minimum:

* use HTTPS;
* avoid committed secrets;
* disable production debugging;
* avoid exposing stack traces;
* avoid exposing internal configuration;
* restrict administrative functionality if any exists;
* use the minimum required external services.

The pilot does not require a full security audit.

---

# 44. Data Minimization

The pilot should collect only the learner information required to operate and evaluate the current experience.

The application should not introduce unnecessary personal-data collection.

The team should avoid collecting:

* unnecessary identity information;
* unnecessary demographic information;
* unnecessary tracking data.

If learner feedback is collected externally, the same principle should apply.

---

# 45. Pilot Exit Criteria

The pilot phase is ready to begin when:

* [ ] A stable HTTPS URL exists.
* [ ] The application can be opened without developer intervention.
* [ ] Existing demo activities are available.
* [ ] The complete learner journey works through the public deployment.
* [ ] Persistence behaviour is understood.
* [ ] Basic application logs are available.
* [ ] Debugging output is disabled for learners.
* [ ] The application can recover from a normal restart.
* [ ] Mobile layout has been verified.
* [ ] Keyboard accessibility has been verified.
* [ ] Existing automated tests pass.
* [ ] The deployment process is documented.
* [ ] The team has a lightweight feedback-recording mechanism.
* [ ] Learner instructions are prepared.
* [ ] Pilot participants can be invited.

---

# 46. Definition of Done

SPEC-014 is complete when:

1. Fablit is accessible through a stable HTTPS URL.
2. A learner can access the application without technical setup.
3. A learner can independently complete the existing learner journey.
4. The deployed experience matches the current SPEC-013 implementation.
5. The deployment does not expose development-only information.
6. Basic operational logs are available.
7. The deployment process is documented.
8. The current application can be restarted or redeployed reproducibly.
9. The team can invite a small group of learners.
10. The team has a defined method for recording learner observations and feedback.

---

# 47. Success Criteria

The technical success criterion is:

> **A real learner can open Fablit and complete an activity without developer assistance.**

The product success criterion is intentionally deferred.

The pilot should not attempt to prove that Fablit is already a successful learning product.

Instead, it should allow us to discover:

> **What does Fablit need to become a better learning product?**

---

# 48. Architectural Outcome

SPEC-014 does not introduce a new domain capability.

It establishes an operational boundary around the existing system:

```text
                    Real Learner
                         │
                         ▼
                   Public HTTPS
                         │
                         ▼
                  Fablit Web/UI
                         │
                         ▼
                   Application
                         │
                         ▼
                      Domain
                         │
                         ▼
                   Persistence
```

The deployment environment exists to expose the existing architecture safely enough for pilot usage.

---

# 49. Product Development Outcome

SPEC-014 marks a transition in the development process.

Before the pilot:

```text
Idea
 ↓
Architecture
 ↓
Specification
 ↓
Implementation
 ↓
Tests
```

After the pilot:

```text
Specification
 ↓
Implementation
 ↓
Deployment
 ↓
Real Learners
 ↓
Observation
 ↓
Evidence
 ↓
Finding
 ↓
Next Specification
```

This feedback loop becomes a core part of Fablit's product development process.

---

# 50. North Star

The purpose of deploying Fablit is not simply to put a website online.

It is to make it possible for us to listen to learners.

> **Build enough to learn.
> Put it in front of learners.
> Listen carefully.
> Let evidence shape what we build next.**
