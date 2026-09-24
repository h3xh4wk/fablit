# SPEC-024 — Learner Identity & Private Practice History

**Status:** Proposed
**Area:** Platform / Privacy / Practice History
**Depends on:** SPEC-021 — Persistent Practice History & Learner Review
**Related:** SPEC-022 — Optional Practice Modes & Learner Choice, SPEC-023 — Practice Library Expansion & Skill Coverage

## 1. Objective

Give each Fablit learner a distinct, anonymous identity so that persistent practice history belongs only to that learner.

The first goal is **privacy and isolation**, not account management.

A learner should be able to use Fablit without creating an account, while completed practices and review history remain private to that learner's browser identity.

The design should also leave a clean path for a future recovery or sign-in mechanism without replacing the internal Fablit learner identity.

## 2. Problem

The practice-history persistence layer is already learner-scoped. Repositories and application use cases accept a `learner_id`, and stored completions contain the learner identity.

The current web/application boundary, however, uses a fixed demo learner identity. Consequently, different browser users can currently resolve to the same learner and see the same practice history.

Conceptually:

```
Learner A ─┐
Learner B ─┼──> shared DEMO_LEARNER_ID ──> shared history
Learner C ─┘
```

The identity boundary must therefore move from a fixed demo identity to a distinct learner identity per anonymous learner.

## 3. Goals

### 3.1 Learner isolation

- Every anonymous learner receives a unique, opaque Fablit `learner_id`.
- Practice submission, completion, history listing, and history review use the current learner identity.
- A learner can access only their own practice history.
- A learner cannot retrieve another learner's completion by changing an identifier in a URL or request.

### 3.2 Anonymous-first experience

- No mandatory registration.
- No mandatory email address.
- No password.
- No learner-facing requirement to understand or manage the internal `learner_id`.

### 3.3 Durable application identity

The internal `learner_id` remains the stable ownership key for practice history.

Future mechanisms such as passwordless email access or external identity providers should attach to this identity rather than replace it.

### 3.4 Preserve the existing practice journey

The change must preserve:

```
Choose Practice
  ↓
Observe
  ↓
Submit
  ↓
Evaluation
  ↓
Feedback
  ↓
Reflection
  ↓
Completion
  ↓
History
  ↓
Review
```

Existing Short Drill / Full Practice behaviour from SPEC-022 must remain unchanged.

## 4. Non-goals

This specification does **not** introduce:

- user registration
- passwords
- username/account profiles
- email authentication
- Google, Facebook, X, or other social login
- portable cross-device history
- recommendation engines
- personalization based on learner behaviour
- scoring, mastery, streaks, badges, points, or gamification
- analytics dashboards
- changes to the practice content model
- changes to the Assessment Activity journey

Portable history and optional external identity can be addressed in later specifications.

## 5. Identity model

### 5.1 Internal learner identity

Generate a high-entropy, opaque identifier for each anonymous learner.

The identifier must:

- be unique with practical collision resistance;
- not encode personal information;
- not be derived from email, name, IP address, device fingerprint, or other identifying data;
- remain stable for the lifetime of the anonymous browser identity.

The existing application/repository contract should continue to use `learner_id` as the ownership boundary.

### 5.2 Browser persistence

The anonymous learner identity should be persisted using a secure browser cookie/session mechanism appropriate to the application's deployment model.

The implementation should:

- avoid exposing unnecessary identity information to client-side JavaScript;
- use appropriate `Secure`, `HttpOnly`, and `SameSite` protections where applicable;
- avoid placing the raw learner identity in normal learner-facing URLs;
- define a sensible lifetime/rotation policy;
- create a new learner identity when no valid learner identity is available.

The exact cookie/session implementation is an implementation decision, provided the privacy and isolation requirements are met.

### 5.3 No cross-device promise yet

An anonymous browser identity is intentionally local to the browser/device context.

Changing device or clearing browser storage may create a new anonymous learner identity in this phase.

Cross-device recovery is explicitly deferred.

## 6. Application boundary

The fixed `DEMO_LEARNER_ID` must no longer be used as the learner identity for normal web requests.

The web/application layer should resolve the current learner identity from the request/session boundary and construct or access the learner-scoped application services using that identity.

The existing repository/application contracts should remain learner-scoped.

Preferred conceptual flow:

```
HTTP request
   ↓
Resolve anonymous learner identity
   ↓
LearnerJourneyStore(learner_id)
   ↓
PracticeApplication
   ↓
Learner-scoped persistence
```

The identity resolution mechanism should be centralized rather than duplicated across individual routes.

## 7. Privacy requirements

### 7.1 History list

`/history` must display only completions belonging to the current learner.

### 7.2 Individual review

A completion belonging to another learner must not be accessible through its completion ID.

The application should return the same externally appropriate not-found behaviour used for an unknown completion rather than revealing whether another learner's completion exists.

### 7.3 Direct URL manipulation

Changing a completion ID in a browser URL must not allow access to another learner's record.

### 7.4 No shared demo history

The production learner experience must not fall back to a single shared learner identity.

If demo fixtures are retained for development/testing, they must remain explicitly isolated from normal anonymous learner traffic.

## 8. Required tests

Add automated tests covering at least the following scenario:

```
Learner A
  completes Practice X

Learner B
  completes Practice Y

Learner A → /history
  sees X
  does not see Y

Learner B → /history
  sees Y
  does not see X

Learner A → /history/Y
  receives not-found behaviour

Learner B → /history/X
  receives not-found behaviour
```

Also verify:

- two fresh clients receive different learner identities;
- the same client retains the same learner identity across requests;
- completion submission is attributed to the current learner;
- history remains scoped after navigation;
- repeated practices remain separate within the same learner;
- an invalid completion ID still behaves correctly;
- persistence failures remain handled as before;
- existing SPEC-021 and SPEC-022 journey tests continue to pass.

Where practical, test identity resolution independently from practice-history behaviour so failures clearly identify whether the problem is in identity creation, request resolution, or persistence scoping.

## 9. Security and observability considerations

The implementation should treat `learner_id` as an internal ownership identifier, not as an authentication credential.

For debugging:

- structured logs may include an opaque learner ID and completion ID where useful;
- do not log submitted response text by default;
- do not log email addresses or future external identity credentials as part of this specification;
- avoid exposing learner IDs unnecessarily in user-facing responses.

Future recovery/authentication mechanisms must not be assumed to exist merely because an anonymous learner ID exists.

## 10. Future portability boundary

This specification intentionally prepares Fablit for a later portable-history flow.

Future architecture should be able to represent a relationship conceptually similar to:

```
External access method
(email / external identity)
          ↓
     Fablit learner_id
          ↓
practice history
```

The external identity must not become the primary practice-history key.

A future specification may introduce:

- passwordless email magic links;
- recovery codes;
- optional external identity providers;
- identity linking;
- account recovery and identity-merge rules.

Those mechanisms are out of scope here.

## 11. Acceptance criteria

SPEC-024 is complete when:

1. A normal anonymous browser session receives a unique learner identity.
2. The identity persists across normal requests from that browser.
3. Two independent learners receive different identities.
4. Practice submissions and completions are stored under the correct learner identity.
5. History lists contain only the current learner's completions.
6. Individual completion review cannot cross learner boundaries.
7. Direct URL/request manipulation cannot bypass learner ownership checks.
8. The fixed shared demo learner identity is no longer used for normal learner traffic.
9. Automated tests explicitly demonstrate two-learner isolation.
10. Existing practice submission, evaluation, reflection, completion, history, and review behaviour remains intact.
11. No registration, email login, social login, recommendation engine, gamification, or cross-device recovery is introduced by this change.

## 12. Implementation guidance

Prefer the smallest change that establishes a reliable identity boundary.

Do not redesign the persistence layer unless an actual implementation constraint requires it. SPEC-021 already established learner-scoped persistence; this specification primarily connects that existing boundary to real web requests.

The implementation should preserve the existing FastAPI + HTMX architecture and avoid introducing an account-management subsystem prematurely.

## 13. Design principle

> **Anonymous does not have to mean shared.**

Fablit should be able to remember a learner's practice history without requiring Fablit to know the learner's real-world identity.
