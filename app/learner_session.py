"""Anonymous learner identity resolution for the web layer (SPEC-024 §6).

The fixed demo learner identity is no longer used for normal web requests:
each browser receives a unique, opaque learner identity carried in a secure
cookie, and the application resolves the learner-scoped boundary from that
identity on every request:

```
HTTP request
   ↓
resolve anonymous learner identity (cookie, or a newly minted one)
   ↓
LearnerJourneyStore(learner_id) inside a per-learner PracticeApplication
   ↓
learner-scoped persistence (SPEC-021 history repository)
```

Learner journey state (submissions, feedback, reflections) and durable
practice history are therefore private to each anonymous learner's browser
identity. Two fresh clients never share a learner, and one learner cannot
reach another learner's completion by manipulating a URL (SPEC-024 §7).

The demo activity content, skills, evaluator wiring, and stimulus provider
are identical for every learner and process-wide immutable, so they are
built once and shared; only learner-scoped state is per learner.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from threading import Lock
from uuid import UUID, uuid4

from fastapi import Request, Response

from fablit.application import (
    DemoEvaluator,
    LearnerJourneyStore,
    PracticeApplication,
    StimulusProvider,
    build_demo_activities,
    build_demo_activity_map,
    build_demo_skills,
    build_stimulus_provider,
)
from fablit.application.persistence import PracticeHistoryRepository
from fablit.application.store import DemoActivity
from fablit.config import AppConfig
from fablit.domain import Skill
from fablit.platform.learner_identity import (
    generate_learner_id,
    read_learner_id_from_cookie,
    set_learner_cookie,
)

logger = logging.getLogger("fablit.app")

#: ``request.state`` key carrying the resolved anonymous learner identity for
#: the current request. The identity is opaque and internal (SPEC-024 §9): it
#: is never rendered in learner-facing pages, never placed in URLs, and never
#: logged.
LEARNER_ID_STATE_KEY = "learner_id"


@dataclass(frozen=True)
class DemoContent:
    """Process-wide, learner-independent demo content and wiring (§6).

    Built once per application assembly and shared by every learner's
    application instance: the seeded activities and skills are identical for
    all learners, as are the evaluator wiring and the stimulus provider. Only
    learner-scoped state lives in per-learner instances.
    """

    activities: tuple[DemoActivity, ...]
    skills: tuple[Skill, ...]
    evaluator: DemoEvaluator
    stimulus_provider: StimulusProvider

    @classmethod
    def build(cls, app_config: AppConfig) -> DemoContent:
        activities = build_demo_activities()
        return cls(
            activities=activities,
            skills=build_demo_skills(),
            evaluator=DemoEvaluator(build_demo_activity_map(activities)),
            stimulus_provider=build_stimulus_provider(
                activities,
                provider_name=app_config.stimulus_provider,
                fallback_image_overrides=app_config.stimulus_fallback_images,
                wikimedia_endpoint=app_config.wikimedia_endpoint,
                wikimedia_timeout=app_config.wikimedia_timeout,
                wikimedia_width=app_config.wikimedia_width,
                wikimedia_limit=app_config.wikimedia_limit,
            ),
        )


class LearnerApplicationRegistry:
    """Resolve a learner identity to its learner-scoped application (§6).

    Each distinct anonymous learner receives its own ``PracticeApplication``
    backed by its own ``LearnerJourneyStore(learner_id)`` and — through it —
    its own learner-scoped view of the shared history repository, so
    in-flight journey state never crosses learner boundaries. Content wiring
    is shared from :class:`DemoContent`; only learner-scoped state is
    per learner.

    The registry is thread-safe and keeps only live learner applications.
    The map is intentionally unbounded for the pilot: each entry is small and
    the deployment is a single-process pilot with a handful of learners
    (SPEC-014). A production hardening would add eviction.
    """

    def __init__(
        self,
        content: DemoContent,
        history_repository: PracticeHistoryRepository | None,
    ) -> None:
        self._content = content
        self._history_repository = history_repository
        self._applications: dict[UUID, PracticeApplication] = {}
        self._lock = Lock()

    def application_for(self, learner_id: UUID) -> PracticeApplication:
        """Return the learner-scoped application, building it on first use."""
        with self._lock:
            application = self._applications.get(learner_id)
            if application is None:
                application = self._build_application(learner_id)
                self._applications[learner_id] = application
                logger.info(
                    "learner application created",
                    extra={"learner_id": str(learner_id)},
                )
            return application

    def _build_application(self, learner_id: UUID) -> PracticeApplication:
        content = self._content
        return PracticeApplication(
            store=LearnerJourneyStore(
                learner_id=learner_id,
                activities=content.activities,
                skills=content.skills,
            ),
            evaluator=content.evaluator,
            stimulus_provider=content.stimulus_provider,
            history_repository=self._history_repository,
        )


async def learner_identity_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Resolve the anonymous learner identity for the request (SPEC-024 §6).

    The identity is read from the browser's learner cookie; a request without
    one is treated as a new anonymous learner and receives a freshly minted
    opaque identity, persisted as a cookie on the response (§5.2: HttpOnly,
    SameSite=Lax, one-year lifetime, and Secure in production). The resolved
    identity travels to route handlers via ``request.state`` and is never
    rendered, never placed in URLs, and never logged (§9).

    Installed through ``app.middleware("http")``, so ``call_next`` is
    Starlette's ``RequestResponseEndpoint``.
    """
    config: AppConfig = request.app.state.config
    learner_id = read_learner_id_from_cookie(request.headers.get("cookie"))
    if learner_id is None:
        learner_id = generate_learner_id()
        is_new_identity = True
    else:
        is_new_identity = False
    # Starlette's State stores arbitrary attributes in the request scope,
    # visible to the route handler's own Request instance.
    request.state.learner_id = learner_id

    response = await call_next(request)
    if is_new_identity:
        set_learner_cookie(
            response,
            learner_id,
            secure=config.environment == "production",
        )
    return response


def learner_id_for_request(request: Request) -> UUID:
    """Return the anonymous learner identity resolved for this request (§5.1)."""
    learner_id = getattr(request.state, LEARNER_ID_STATE_KEY, None)
    if isinstance(learner_id, UUID):
        return learner_id
    # The identity middleware did not run for this request (for example a
    # route invoked outside the normal request path in tests). A transient
    # identity keeps such requests learner-scoped and safe by default.
    return uuid4()


def practice_for_request(request: Request) -> PracticeApplication:
    """Resolve the current learner's practice application (SPEC-024 §6)."""
    registry: LearnerApplicationRegistry = request.app.state.learner_applications
    return registry.application_for(learner_id_for_request(request))
