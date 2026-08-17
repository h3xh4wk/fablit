# SPEC-015 — Contextual Visual Stimulus & Response-Aware Evaluation

The key architectural decision is that **the image is part of the learner's activity instance**, not merely an attachment to an activity.

And for the first implementation, I would keep the external image retrieval deliberately conservative:

* approved source rather than arbitrary web scraping;
* contextual query defined by the activity;
* deterministic enough to test;
* selected stimulus persisted;
* source/license/attribution metadata retained;
* the same resolved stimulus can be revisited later;
* response-aware evaluation produces at least one structured Finding.

Most importantly, **we should not build a sophisticated AI evaluator yet**. SPEC-015 should establish the contract that later evaluators—rule-based, AI-assisted, or hybrid—can implement.

Here is the complete specification:

````markdown
# SPEC-015 — Contextual Visual Stimulus & Response-Aware Evaluation

**Specification ID:** SPEC-015
**Title:** Contextual Visual Stimulus & Response-Aware Evaluation
**Version:** 0.1.0
**Status:** Draft
**Priority:** High
**Epic:** Learner Validation

---

## 1. Purpose

SPEC-015 extends the learner experience established by SPEC-012, SPEC-013, and SPEC-014.

The current Fablit pilot demonstrates the learner journey, but two important limitations have been identified:

1. Some activities require learners to observe or analyse an image that is not currently presented to them.
2. Feedback is currently predefined rather than meaningfully related to the learner's submitted response.

This specification introduces the minimum capability required to address both problems.

The objective is to establish the following learning loop:

```text
Activity
   ↓
Contextual stimulus
   ↓
Learner observes
   ↓
Learner responds
   ↓
Response-aware evaluation
   ↓
Structured Finding
   ↓
Personalized feedback
   ↓
Reflection
   ↓
Completion
````

---

# 2. Product Intent

The learner should feel that Fablit is responding to **what they actually did**, rather than displaying a generic answer after submission.

The intended experience is:

> **The learner observes something, forms an interpretation, shares it, and receives feedback about their particular response.**

The system should also preserve the stimulus that the learner actually saw so that the activity can later be revisited, reviewed, or evaluated.

---

# 3. Scope

SPEC-015 introduces:

1. contextual visual stimulus requirements;
2. external image retrieval;
3. stimulus metadata;
4. stimulus preservation;
5. association between a learner activity instance and its stimulus;
6. response-aware evaluation;
7. structured Findings derived from the learner response;
8. feedback based on those Findings;
9. tests covering the complete flow.

---

# 4. Explicit Non-Goals

SPEC-015 does not introduce:

* a general-purpose media management platform;
* arbitrary web scraping;
* unrestricted image search;
* a production content moderation system;
* a sophisticated recommendation engine;
* a full AI evaluation platform;
* learner ranking;
* scoring;
* gamification;
* instructor dashboards;
* analytics;
* subscriptions;
* payments;
* social features;
* a full content management system;
* multiple external image providers unless required by the implementation;
* automatic generation of every future Fablit activity.

The implementation should remain intentionally small.

---

# 5. Core Principle

> **The activity defines the learning context. The system resolves the stimulus. The learner responds to the stimulus. The evaluation responds to the learner.**

This creates four distinct responsibilities:

```text
Activity
   │
   │ defines
   ▼
Learning Context
   │
   │ resolves
   ▼
Stimulus
   │
   │ observed by
   ▼
Learner Response
   │
   │ evaluated against
   ▼
Evaluation
```

---

# 6. Activity Context

An activity shall be capable of defining enough contextual information to identify an appropriate visual stimulus.

The activity may define:

* skill;
* learning focus;
* stimulus context;
* retrieval query;
* optional stimulus characteristics.

Example:

```text
Skill:
Visual Analysis

Learning focus:
Composition

Stimulus context:
Fashion editorial photography

Retrieval query:
fashion editorial composition
```

The exact domain representation is an implementation decision.

---

# 7. Stimulus Requirements

A visual stimulus shall provide the learner with the material necessary to perform the activity.

For an activity that asks the learner to observe or analyse an image:

> **The image is part of the activity experience.**

It must not be treated as optional decorative content.

---

# 8. External Stimulus Retrieval

Fablit may retrieve an appropriate visual stimulus from an approved external source.

The first implementation should use **one approved source**.

The external provider should support:

* stable image identification;
* image URL;
* source page;
* creator/author information where available;
* license information where available;
* attribution information where available.

The implementation should avoid generic image-search scraping.

---

# 9. Provider Abstraction

External image retrieval shall be isolated behind an application-level abstraction.

The domain should not depend directly on a specific image provider.

Conceptually:

```text
Application
    │
    ▼
Stimulus Provider
    │
    ▼
External Image Source
```

This allows the provider to be replaced later without changing the learner activity model.

---

# 10. Provider Selection

The initial implementation may use a source such as Wikimedia Commons or another provider that supports appropriate reuse and metadata.

The exact provider is an implementation decision.

The provider must satisfy the minimum requirements defined in this specification.

---

# 11. Contextual Retrieval

The retrieval mechanism shall use the activity's context rather than requesting an arbitrary random image.

The retrieval request should be derived from information such as:

```text
Skill
Learning focus
Stimulus context
Retrieval query
```

The objective is:

> **Relevant variation rather than unrestricted randomness.**

---

# 12. Randomness

Random selection may be used within the set of contextually relevant candidate images.

It must not mean:

> Search the entire web and select any image that appears relevant.

The retrieval process should remain bounded by the activity's learning context.

---

# 13. Candidate Selection

The implementation may retrieve one or more candidate images before selecting a stimulus.

The selection mechanism should prioritize:

1. contextual relevance;
2. availability;
3. reusable licensing;
4. sufficient metadata;
5. stable identification.

The first implementation does not require sophisticated ranking.

---

# 14. Stimulus Resolution

When an activity is started, Fablit may resolve a visual stimulus.

Conceptually:

```text
Activity
   ↓
Stimulus Context
   ↓
Provider Query
   ↓
Candidate Image(s)
   ↓
Selected Stimulus
```

Once selected, the stimulus becomes part of the learner's activity instance.

---

# 15. Stimulus Instance

A resolved stimulus shall be represented separately from the reusable activity definition.

Conceptually:

```text
Activity
   │
   └── Stimulus Instance
          │
          ├── Image
          ├── Source
          ├── Attribution
          ├── License
          └── Retrieval metadata
```

This distinction allows one activity to use different stimuli over time without losing the identity of the specific stimulus shown to a learner.

---

# 16. Stimulus Persistence

Once a stimulus has been presented to a learner, Fablit shall retain enough information to identify what the learner saw.

At minimum, the system should preserve:

* provider;
* provider asset identifier where available;
* image URL;
* source page URL;
* creator/author where available;
* license information where available;
* attribution information where available;
* retrieval timestamp.

---

# 17. URL Preservation

The system should preserve the direct image URL when the provider supplies one.

The system should also preserve the source page URL.

These have different purposes:

```text
Image URL
    ↓
What was displayed?

Source URL
    ↓
Where did it come from?
```

---

# 18. Historical Reference

A learner's completed activity should remain associated with the stimulus that was shown at the time.

The system should not silently replace the historical stimulus with a newly retrieved image.

Example:

```text
Learner Activity Instance
        │
        ├── Activity
        ├── Response
        ├── Evaluation
        └── Stimulus Instance
```

This ensures that later revision remains meaningful.

---

# 19. Stimulus Reuse

The same resolved stimulus may be reused when the learner revisits an existing activity instance.

A new stimulus may be resolved when starting a new activity instance, subject to the activity's retrieval policy.

The exact lifecycle policy may remain simple in the first implementation.

---

# 20. Licensing and Attribution

The implementation shall retain licensing and attribution information provided by the external source.

The learner-facing experience should display attribution when required by the source's licensing terms.

Attribution should not unnecessarily distract from the learning experience.

A compact source/attribution treatment is preferred.

---

# 21. Provider Failure

External image retrieval may fail.

Fablit shall handle provider failure gracefully.

The learner should not see:

* stack traces;
* provider credentials;
* internal exception details;
* raw HTTP error responses.

The application should provide a learner-safe fallback.

---

# 22. Stimulus Fallback

The first implementation should define a deterministic fallback for cases where external retrieval fails.

Possible fallback behaviour:

```text
External retrieval succeeds
        ↓
Use resolved stimulus

External retrieval fails
        ↓
Use known fallback stimulus
```

The fallback should still satisfy the activity's learning purpose.

The implementation should not leave the learner with a blank activity when a valid fallback is available.

---

# 23. No Arbitrary Placeholder

If no suitable stimulus can be resolved and no valid fallback exists, Fablit should not present an activity that requires an image while silently omitting the image.

The learner should instead receive a clear, learner-safe message.

---

# 24. Learner Presentation

The stimulus should be presented before the learner is asked to analyse it.

The intended order is:

```text
Activity invitation
       ↓
Stimulus
       ↓
Observation prompt
       ↓
Response field
```

The learner should not have to infer that an external image exists.

---

# 25. Visual Presentation

The image should:

* be clearly visible;
* preserve an appropriate aspect ratio;
* remain usable on smaller screens;
* not overflow the viewport;
* have meaningful alternative text where appropriate.

The exact visual treatment remains part of the learner experience established in SPEC-013.

---

# 26. Accessibility

The visual stimulus must have an accessible representation.

The implementation should provide meaningful alternative text where the image content can be described appropriately.

If the image is inherently the subject of visual analysis, the implementation should avoid providing alternative text that gives away the intended observation unnecessarily.

Accessibility and learning integrity should both be considered.

---

# 27. Response-Aware Evaluation

The evaluation system shall receive, at minimum:

```text
Activity
Stimulus
Learner Response
```

Conceptually:

```text
Activity
   +
Stimulus
   +
Learner Response
        │
        ▼
    Evaluation
```

The evaluator must not evaluate the response in isolation when the activity depends on the stimulus.

---

# 28. Evaluation Contract

The evaluation contract shall remain independent of the specific evaluation technology.

An evaluator may be:

* rule-based;
* deterministic;
* AI-assisted;
* hybrid.

SPEC-015 does not mandate a particular implementation technology.

---

# 29. Structured Finding Requirement

Every successful evaluation shall produce at least one structured Finding.

A Finding must relate to the learner's submitted response.

A Finding should identify something observable about the response, such as:

* an element the learner noticed;
* a relevant concept they identified;
* a meaningful interpretation;
* an omission;
* a misconception;
* an opportunity for deeper observation.

---

# 30. Finding Quality

A Finding should not simply repeat the generic activity feedback.

For example, this is insufficient:

```text
Finding:
Good job analysing the image.
```

A stronger Finding would be:

```text
Finding:
You noticed the contrast between the foreground figure
and the quieter background, which is an important part
of the composition.
```

The exact wording is implementation-dependent.

The important requirement is:

> **The Finding must be grounded in the learner's actual response.**

---

# 31. Evidence

Where practical, a Finding should retain enough evidence to explain why it was produced.

Conceptually:

```text
Finding
   │
   ├── Statement
   ├── Evidence
   └── Optional rationale
```

Evidence may be:

* a response excerpt;
* a matched concept;
* a structured observation;
* another evaluator-supported reference.

The implementation should avoid storing unnecessary sensitive data.

---

# 32. Multiple Findings

The evaluation may produce multiple Findings.

However, the first implementation should avoid overwhelming the learner.

The learner-facing feedback should prioritize the most useful findings.

A small number of meaningful findings is preferable to a long evaluation report.

---

# 33. Feedback Generation

Feedback shall be derived from the Findings.

Conceptually:

```text
Learner Response
       ↓
Evaluation
       ↓
Findings
       ↓
Feedback
```

This preserves the architecture established by earlier specifications.

---

# 34. Feedback Tone

Feedback must preserve the learner experience principles established in SPEC-013.

Feedback should feel:

* encouraging;
* curious;
* specific;
* conversational;
* non-judgmental.

Feedback should avoid:

* grades;
* marks;
* rankings;
* pass/fail language;
* loss language;
* overly academic assessment terminology.

---

# 35. Personalized Feedback

Personalization does not mean using the learner's name or inserting superficial personalization.

For SPEC-015:

> **Personalized feedback means feedback that meaningfully reflects the learner's submitted response.**

For example:

```text
Learner response:
"I notice that the person stands out because
the background is much darker."

Feedback:
"Your observation about the darker background is
important. You identified how contrast helps direct
attention toward the figure."
```

---

# 36. Reflection

The existing reflection step from SPEC-012 and SPEC-013 remains part of the learner journey.

The evaluation should not replace reflection.

The intended flow remains:

```text
Respond
  ↓
Receive feedback
  ↓
Reflect
  ↓
Complete
```

---

# 37. Completion Experience

The existing accomplishment-oriented completion experience remains unchanged.

The learner should continue to experience completion as:

> **A small accomplishment rather than a score.**

The implementation should not introduce points or grades as part of SPEC-015.

---

# 38. Learner Journey

The complete SPEC-015 journey becomes:

```text
Dashboard
    ↓
Choose activity
    ↓
Resolve contextual stimulus
    ↓
Display stimulus
    ↓
Learner observes
    ↓
Learner submits response
    ↓
Evaluate response + stimulus + activity
    ↓
Produce structured Finding(s)
    ↓
Generate learner-facing feedback
    ↓
Reflect
    ↓
Complete
```

---

# 39. Domain Boundary

The domain layer should represent the concepts required to reason about:

* activity;
* stimulus;
* learner response;
* evaluation;
* Finding.

The domain must not depend on:

* HTTP;
* FastAPI;
* a specific image provider;
* browser rendering;
* provider-specific APIs;
* external network calls.

---

# 40. Application Boundary

The application layer should coordinate:

```text
Activity
   ↓
Stimulus resolution
   ↓
Learner interaction
   ↓
Evaluation
   ↓
Feedback
```

External providers should be accessed through abstractions.

---

# 41. Infrastructure Boundary

External image providers belong outside the domain.

Conceptually:

```text
                Domain
                  │
                  ▼
             Application
              /       \
             /         \
            ▼           ▼
Stimulus Provider    Evaluator
            │           │
            ▼           ▼
      External API   Evaluation
```

The exact module structure is an implementation decision.

---

# 42. Determinism for Testing

External randomness should not make the automated test suite unreliable.

Tests should be able to provide a deterministic stimulus.

For example:

```text
Test
  ↓
Fake Stimulus Provider
  ↓
Known Image
```

The production provider may retrieve external content.

Tests must not depend on the external provider being available.

---

# 43. Provider Abstraction for Tests

The application should allow the external stimulus provider to be replaced with a fake or deterministic implementation during testing.

This allows tests to verify:

* stimulus resolution;
* persistence;
* learner presentation;
* evaluation;
* feedback;

without making network requests.

---

# 44. Evaluation Abstraction for Tests

The evaluation mechanism should similarly be replaceable for deterministic tests.

A fake evaluator may produce known Findings.

This allows the application flow to be tested independently of the final evaluation technology.

---

# 45. Error Isolation

A failure in stimulus retrieval should not corrupt the learner's activity state.

A failure in evaluation should not expose internal implementation details.

The application should preserve clear boundaries between:

```text
Stimulus failure
Evaluation failure
Presentation failure
```

---

# 46. Persistence Strategy

SPEC-015 does not require introducing a production database.

The existing persistence strategy may continue to be used for the pilot if it can retain the stimulus metadata and evaluation result for the relevant learner activity instance.

A database should only be introduced if the current architecture cannot satisfy the required historical reference.

---

# 47. Data Model Expectations

The implementation should conceptually support:

```text
Activity
    │
    └── Activity Instance
            │
            ├── Stimulus Instance
            │       ├── Provider
            │       ├── Asset ID
            │       ├── Image URL
            │       ├── Source URL
            │       ├── Creator
            │       ├── License
            │       └── Retrieved At
            │
            ├── Learner Response
            │
            └── Evaluation
                    │
                    └── Findings
```

The exact persistence model may differ.

---

# 48. Historical Integrity

A completed learner activity must remain internally consistent.

At minimum:

```text
Response
   ↓
was submitted for
   ↓
Activity Instance
   ↓
used
   ↓
Stimulus Instance
   ↓
produced
   ↓
Evaluation
```

The system must not later associate the response with a different stimulus without an explicit migration or replacement process.

---

# 49. External Dependency Boundary

The learner experience should not directly depend on the external provider's API response format.

Provider-specific fields should be translated into Fablit's internal stimulus representation.

This prevents external API details from leaking into the domain.

---

# 50. Network Failure

External network access may be unavailable.

The application should handle:

* timeout;
* unavailable provider;
* invalid provider response;
* missing image;
* missing metadata.

The failure must not produce an unhandled exception visible to the learner.

---

# 51. Image Validation

The implementation should perform basic validation before presenting a retrieved image.

At minimum, it should verify that:

* a usable image URL exists;
* the provider returned an identifiable asset;
* required metadata is available where required;
* the image can reasonably be presented to the learner.

Sophisticated computer-vision validation is outside the scope.

---

# 52. Content Suitability

The retrieval mechanism should use the provider's available metadata and the activity context to reduce obviously irrelevant results.

The first implementation does not require a complete automated content moderation system.

However, the system should not intentionally request unrestricted or unsafe content.

Activity queries should be authored within the intended educational context.

---

# 53. Reproducibility

A completed activity should provide enough information for developers to determine:

> **Which external stimulus was shown to this learner?**

This is important for:

* debugging;
* learner revision;
* evaluation analysis;
* future pilot research;
* understanding feedback.

---

# 54. Revision

When a learner revisits a completed activity, Fablit should be able to show the original stimulus associated with that completed activity.

A future revision mode may optionally provide a new stimulus.

Such a capability is outside SPEC-015.

---

# 55. Pilot Limitation

The first implementation may support only one stimulus type:

> **Image**

Future stimulus types such as:

* video;
* article;
* garment;
* object;
* screenshot;
* illustration;

may be introduced later.

The abstraction should not prevent such evolution, but SPEC-015 should implement only what is necessary.

---

# 56. Pilot Activity

At least one existing Fablit activity shall be upgraded to use the new stimulus and response-aware evaluation flow.

This activity becomes the reference implementation for the architecture.

---

# 57. Reference Activity

The reference activity should:

1. require visual observation;
2. display an actual image;
3. ask an open-ended learner response;
4. evaluate that response;
5. produce at least one structured Finding;
6. display feedback derived from the Finding;
7. allow reflection;
8. complete normally.

---

# 58. Reference Activity Example

A suitable example may be:

```text
Activity:
Look at the image and notice how the composition
directs your attention.

Prompt:
What catches your eye first, and what in the image
makes you notice it?
```

The exact activity content is an implementation/content decision.

The important property is that the learner's answer can be meaningfully evaluated against the visual stimulus.

---

# 59. Structured Finding Example

Given:

```text
Learner response:
"The model stands out because she is surrounded
by a lot of empty space."
```

A structured Finding might be:

```text
Finding:
You noticed the use of negative space around the
figure and connected it to visual emphasis.
```

The learner should then receive feedback derived from that observation.

---

# 60. Evaluation Independence

SPEC-015 establishes the evaluation contract but does not lock Fablit into a particular evaluator implementation.

The following are all valid future implementations:

```text
Rule-based evaluator
AI evaluator
Hybrid evaluator
Human evaluator
```

The current implementation should provide the smallest viable evaluator capable of demonstrating response-aware Findings.

---

# 61. No False Personalization

The implementation must not claim personalization when the feedback is merely generic.

For example:

```text
"You made a good observation."
```

is not sufficient by itself.

The response should influence the feedback content.

---

# 62. Empty Response

If the learner submits an empty or effectively empty response, the evaluator should handle it explicitly.

It should not generate a fabricated positive Finding.

The learner should receive an appropriate prompt encouraging them to add an observation.

---

# 63. Very Short Responses

Very short responses should be handled gracefully.

The evaluator may produce a Finding that encourages elaboration.

For example:

```text
"You noticed the figure. What specifically makes
the figure stand out to you?"
```

The exact wording is implementation-dependent.

---

# 64. Evaluation Failure

If evaluation fails after a valid learner response has been submitted, the learner should not lose their response.

The system should preserve the response where possible and provide a learner-safe message.

---

# 65. Feedback Failure

If feedback generation fails after Findings have been produced, the system should avoid losing the Findings.

The implementation may fall back to a simple presentation of the available feedback information.

---

# 66. Test Requirements

Tests shall cover the complete reference flow.

At minimum:

### Stimulus

* activity specifies stimulus context;
* provider returns a stimulus;
* stimulus metadata is normalized;
* stimulus is presented;
* stimulus is persisted.

### Response

* learner submits a response;
* response is associated with the activity instance;
* response is associated with the correct stimulus instance.

### Evaluation

* evaluator receives activity;
* evaluator receives stimulus;
* evaluator receives learner response;
* evaluator produces at least one Finding.

### Feedback

* feedback is derived from the Finding;
* feedback is not purely generic;
* learner can continue to reflection and completion.

---

# 67. External Provider Tests

The automated test suite must not depend on the live external image provider.

Provider integration tests may exist separately.

The main application tests should use a fake provider.

---

# 68. Historical Reference Test

A test shall verify that:

1. a stimulus is resolved;
2. a learner responds;
3. the activity is completed;
4. the original stimulus metadata remains associated with the completed activity.

---

# 69. Response-Specific Test

At least one test shall demonstrate that different learner responses can result in different Findings.

For example:

```text
Response A
    ↓
Finding A

Response B
    ↓
Finding B
```

This is an important acceptance criterion.

The system must demonstrate that evaluation is not simply returning the same predefined feedback regardless of input.

---

# 70. Regression Tests

All existing tests from previous specifications shall continue to pass.

SPEC-015 must not regress:

* application boundaries;
* existing learner navigation;
* completion behaviour;
* accessibility;
* responsive behaviour;
* production configuration.

---

# 71. Browser Test

At least one browser-level test shall verify:

```text
Open activity
   ↓
See image
   ↓
Enter response
   ↓
Submit
   ↓
See response-aware feedback
   ↓
Reflect
   ↓
Complete
```

The browser test may use deterministic provider/evaluator implementations.

---

# 72. Acceptance Criteria

SPEC-015 is accepted when:

* [ ] At least one activity defines contextual visual stimulus requirements.
* [ ] The activity can resolve an image through an approved provider.
* [ ] The learner can see the resolved image.
* [ ] Image metadata is retained.
* [ ] The learner activity instance retains the stimulus reference.
* [ ] The source and attribution information can be identified later.
* [ ] External provider failures are handled safely.
* [ ] Tests do not depend on the live image provider.
* [ ] The learner response reaches the evaluator.
* [ ] The evaluator receives the relevant activity context.
* [ ] The evaluator receives the actual stimulus.
* [ ] The evaluator receives the learner's actual response.
* [ ] At least one structured Finding is produced.
* [ ] The Finding is related to the learner response.
* [ ] Different responses can produce different Findings.
* [ ] Feedback is derived from the Finding.
* [ ] The learner can continue to reflection.
* [ ] The learner can complete the activity normally.
* [ ] Existing regression tests pass.
* [ ] At least one browser-level test covers the complete flow.

---

# 73. Definition of Done

SPEC-015 is complete when a learner can experience:

```text
See an actual contextual image
        ↓
Observe it
        ↓
Write what they notice
        ↓
Submit
        ↓
Fablit evaluates their response
        ↓
Fablit identifies something specific
        ↓
Fablit responds to that observation
        ↓
Learner reflects
        ↓
Learner completes the activity
```

and the system can later determine:

```text
What activity did they complete?
What stimulus did they see?
What did they write?
What Finding was produced?
What feedback did they receive?
```

---

# 74. Architectural Outcome

SPEC-015 establishes an important relationship in the Fablit model:

```text
Activity
   │
   ├───────────────┐
   │               │
   ▼               ▼
Stimulus       Learner Response
   │               │
   └───────┬───────┘
           ▼
       Evaluation
           │
           ▼
        Findings
           │
           ▼
        Feedback
```

This makes the evaluation meaningful because it has access to the actual learning context.

---

# 75. Product Outcome

SPEC-015 changes the learner experience from:

```text
Question
   ↓
Answer
   ↓
Generic Feedback
```

to:

```text
Context
   ↓
Observation
   ↓
Interpretation
   ↓
Response
   ↓
Specific Finding
   ↓
Meaningful Feedback
```

This is closer to the intended Fablit learning philosophy.

---

# 76. Future Evolution

SPEC-015 intentionally leaves room for future capabilities.

Possible future directions include:

* multiple stimulus providers;
* curated stimulus pools;
* richer image filtering;
* AI-assisted evaluation;
* multimodal evaluation;
* learner-specific difficulty;
* new stimulus types;
* revision with new stimuli;
* evaluation confidence;
* richer structured Findings;
* learning-progress insights.

None of these should be implemented as part of SPEC-015 unless required to satisfy the core acceptance criteria.

---

# 77. North Star

The purpose of this specification is not simply to make images appear on the screen.

It is to establish a more authentic learning interaction:

> **Fablit shows the learner something worth noticing, listens to what they notice, and responds to what they actually said.**

The stimulus gives the learner something real to think about.

The response gives Fablit something real to learn about the learner.

The Finding gives the learner something specific to take away.

And the completion experience remains:

> **I noticed something.
> I thought about it.
> I learned something.
> That's one done.**
