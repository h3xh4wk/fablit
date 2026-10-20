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
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from threading import RLock
from uuid import UUID, uuid4

from fastapi import Request, Response

from fablit.application import (
    ArtifactStorage,
    DemoEvaluator,
    LearnerJourneyStore,
    PracticeApplication,
    PublishedPractice,
    PublishedPracticeStore,
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

    SPEC-035 §6/§9: the explicitly published learner-library practices are
    owned by this registry and refreshed from the ``PublishedPracticeStore``
    on each new learner's first request, so every instance sees the latest
    publications and withdrawals without needing a restart.
    """

    def __init__(
        self,
        content: DemoContent,
        history_repository: PracticeHistoryRepository | None,
        artifact_storage: ArtifactStorage | None = None,
        store: PublishedPracticeStore | None = None,
        publications: tuple[PublishedPractice, ...] = (),
        refresh_interval_seconds: float = 5.0,
    ) -> None:
        self._content = content
        self._history_repository = history_repository
        self._artifact_storage = artifact_storage
        # SPEC-035 §6/§9: publications are owned by this registry and
        # refreshed from the store on each new learner's first request.
        self._store: PublishedPracticeStore | None = store
        self._publications: dict[UUID, PublishedPractice] = {
            record.activity_id: record for record in publications
        }
        self._applications: dict[UUID, PracticeApplication] = {}
        # A re-entrant lock: the registry helpers are called from each other
        # (application creation reads the published set), and a plain
        # non-re-entrant lock would deadlock the request that triggered them.
        self._lock = RLock()
        self._refresh_interval_seconds = refresh_interval_seconds
        self._last_refresh_at = 0.0

    @property
    def publications(self) -> tuple[PublishedPractice, ...]:
        """The current publication records, ordered by catalogue position."""
        with self._lock:
            return self._publication_tuple()

    def _publication_tuple(self) -> tuple[PublishedPractice, ...]:
        # SPEC-035 §9 / issue #144: positions are advisory hints allocated
        # per instance, so concurrent publications can share one. Order ties
        # deterministically by publication time and stable activity identity
        # — the same tie-break as PublishedPracticeStore.list_records — so
        # every instance renders the same catalogue order.
        return tuple(
            sorted(
                self._publications.values(),
                key=lambda record: (
                    record.activity.activity.position,
                    record.published_at,
                    str(record.activity_id),
                ),
            )
        )

    def _should_refresh_publications(self) -> bool:
        if self._store is None:
            return False
        if self._refresh_interval_seconds <= 0:
            return True
        now = time.monotonic()
        return not (now - self._last_refresh_at < self._refresh_interval_seconds)

    def refresh_publications(self, *, force: bool = False) -> None:
        """Refresh this registry's publication state from the store.

        Re-reads the current publication records from the shared
        ``PublishedPracticeStore``, so every application instance sees the
        latest publications and withdrawals without needing a process restart.
        Falls back gracefully to the existing publication set when the store
        is unavailable, preserving the seeded library during outages.

        The store is read before the registry lock is taken: it may be a
        network call, and holding the lock across it would stall every other
        learner (and freeze the request loop while the store is slow). Only
        the in-memory merge runs under the lock.
        """
        if self._store is None:
            logger.debug("no store; keeping existing")
            return
        if not force and not self._should_refresh_publications():
            return
        try:
            records = self._store.list_records()
        except Exception:
            logger.exception(
                "failed to refresh publications from store; keeping existing set"
            )
            return
        with self._lock:
            self._merge_publications(records)
            self._last_refresh_at = time.monotonic()
            logger.info(
                "publications refreshed from store: %d records",
                len(self._publications),
            )

    def _merge_publications(self, records: tuple[PublishedPractice, ...]) -> None:
        """Replace the published set with the store's records.

        Records keep their stable activity identity (SPEC-035 §8), so a
        republished practice replaces its previous entry in place. Records the
        store no longer holds are withdrawn from the learner's view.
        """
        published_ids = {record.activity_id for record in records}
        # Update in-place: keep existing entries, add/new ones replace
        # under their stable activity identity (SPEC-035 §8 replacement policy).
        for record in records:
            self._publications[record.activity_id] = record
        # Remove entries no longer in the store
        keys_to_remove = [key for key in self._publications if key not in published_ids]
        for key in keys_to_remove:
            del self._publications[key]

    def record_publication(self, record: PublishedPractice) -> None:
        """Publish a record to every live learner application (SPEC-035 §5).

        Called only after the publication has been persisted successfully, so
        an in-process view never shows content the store refused to keep.
        Each learner application reconciles on its next request.
        """
        with self._lock:
            self._publications[record.activity_id] = record

    def next_activity_position(self) -> int:
        """The catalogue position a newly published practice should occupy.

        Published practices sort after the seeded library and after anything
        published before them, so first publication order is stable and
        learners always see the curated library first.
        """
        with self._lock:
            positions = [item.activity.position for item in self._content.activities]
            positions.extend(
                record.activity.activity.position
                for record in self._publications.values()
            )
            return max(positions, default=-1) + 1

    def application_for(self, learner_id: UUID) -> PracticeApplication:
        """Return the learner-scoped application, building it on first use."""
        with self._lock:
            application = self._applications.get(learner_id)
        if application is None:
            # SPEC-035 §9: a new learner sees the latest publications and
            # withdrawals, so the published set is refreshed before the
            # application is built. The refresh runs outside the registry
            # lock: the store read may be a network call and must never
            # block the other learners.
            self.refresh_publications(force=True)
        else:
            # Existing learners must also pick up publications and withdrawals
            # from other instances within a bounded refresh window.
            self.refresh_publications()
        with self._lock:
            application = self._applications.get(learner_id)
            if application is None:
                application = self._build_application(learner_id)
                self._applications[learner_id] = application
                logger.info(
                    "learner application created",
                    extra={"learner_id": str(learner_id)},
                )
            else:
                # SPEC-035: pick up publications and withdrawals made since
                # this learner's application was built. Reconciliation is a
                # no-op while the published set is unchanged.
                application.apply_publications(self._publication_tuple())
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
            artifact_storage=self._artifact_storage,
            publications=self._publication_tuple(),
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
