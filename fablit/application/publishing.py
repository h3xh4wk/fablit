"""Publication boundary between approved authoring content and the learner library
(SPEC-035).

Approval and publication are distinct decisions:

- **Approved** records that a human reviewer accepted a candidate's content
  quality (SPEC-032).
- **Published** means that approved, reviewed content has been deliberately
  made available in the learner-facing curated practice library.

Publication is an explicit human action, never a side effect of generation or
approval, and approval alone never makes content learner-visible. This module
owns the smallest representation the handoff needs:

- :class:`PublishableCandidate` — the structural contract a candidate must
  satisfy to cross the boundary, matched by both authoring candidate models.
- :class:`PublishedPractice` — one published practice expressed in the
  *existing* learner-facing :class:`~fablit.application.store.DemoActivity`
  representation plus its source provenance.
- :class:`PublishedPracticeStore` — the publication persistence port.
- :func:`publish_candidate` / :func:`withdraw_publication` — the explicit,
  idempotent publish and withdrawal transitions.

Publication never mutates authoring state and never exposes authoring data to
learners: the learner side only ever sees the published ``DemoActivity``
(provenance stays internal), and ordinary learner practice never depends on
the authoring workflow or an AI provider.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from threading import Lock
from typing import Protocol
from uuid import NAMESPACE_DNS, UUID, uuid5

from fablit.domain import ActivityStatus, ActivityType, AssessmentActivity

from .authoring import CandidateValidation
from .errors import (
    CandidateContentNotPublishableError,
    CandidateNotPublishableError,
    InvalidPublishedPracticeError,
    PublishedPracticeNotFoundError,
)
from .image_search import ImageCandidate
from .persistence import PersistenceError
from .store import DemoActivity, PracticeContentContract

logger = logging.getLogger("fablit.application")


class PublishableCandidate(Protocol):
    """The structural contract an authoring candidate must satisfy at publication.

    Both authoring candidate representations satisfy it — the SPEC-032
    application-layer candidate (``fablit.application.authoring``) and the
    web-layer candidate the running application persists (``app.authoring``) —
    so the publication boundary is written once against the workflow's shape
    rather than against one storage-specific model.
    """

    @property
    def id(self) -> UUID: ...

    @property
    def title(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def contract(self) -> PracticeContentContract | None: ...

    @property
    def is_approved(self) -> bool: ...

    @property
    def revision(self) -> int: ...

    @property
    def status(self) -> str: ...

    @property
    def validation(self) -> CandidateValidation: ...

    @property
    def stimulus(self) -> ImageCandidate | None:
        """The author-selected stimulus image, if there is one (SPEC-036)."""
        ...

    @property
    def supports_sketch_upload(self) -> bool:
        """Whether the published practice should accept a sketch (SPEC-037)."""
        ...


@dataclass(frozen=True)
class PublishedPractice:
    """One explicitly published practice and its provenance (SPEC-035 §6, §8).

    ``activity`` is the existing learner-facing ``DemoActivity`` — publication
    registers curated content, it never introduces a parallel learner practice
    model. Provenance (source candidate, approved revision, publication and
    withdrawal times) is internal authoring data: learners only ever see the
    activity itself.

    The record — not the candidate — owns the published content, so editing
    the source candidate later never silently overwrites what learners see;
    replacement happens only through an explicit republish of a re-approved
    revision, under the same stable activity identity.
    """

    activity: DemoActivity
    source_candidate_id: UUID
    source_revision: int
    published_at: datetime
    withdrawn_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.activity, DemoActivity):
            raise InvalidPublishedPracticeError(
                "published practice must carry the learner-facing activity "
                f"representation (got {type(self.activity).__name__})"
            )
        if not isinstance(self.source_candidate_id, UUID):
            raise InvalidPublishedPracticeError(
                "published practice must trace to a valid source candidate "
                f"identity (got {self.source_candidate_id!r})"
            )
        if (
            isinstance(self.source_revision, bool)
            or not isinstance(self.source_revision, int)
            or self.source_revision < 1
        ):
            raise InvalidPublishedPracticeError(
                "published practice source revision must be at least 1 "
                f"(got {self.source_revision!r})"
            )
        for name in ("published_at", "withdrawn_at"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, datetime) or value.tzinfo is None
            ):
                raise InvalidPublishedPracticeError(
                    f"published practice {name} must be a timezone-aware datetime "
                    f"(got {value!r})"
                )
        if (
            self.withdrawn_at is not None
            and self.published_at is not None
            and self.withdrawn_at < self.published_at
        ):
            raise InvalidPublishedPracticeError(
                "published practice cannot be withdrawn before it was published "
                f"(published_at={self.published_at!r}, "
                f"withdrawn_at={self.withdrawn_at!r})"
            )

    @property
    def activity_id(self) -> UUID:
        """The stable learner-facing identity of this published practice."""
        return self.activity.activity.id

    @property
    def is_withdrawn(self) -> bool:
        """Whether this publication has been withdrawn from discovery."""
        return self.withdrawn_at is not None

    @property
    def is_visible(self) -> bool:
        """Whether learners should discover this practice (published, not withdrawn)."""
        return self.withdrawn_at is None


class PublishedPracticeStore(ABC):
    """Persistence port for published learner-library practices (SPEC-035 §5, §9).

    The application layer depends on this port only; concrete adapters
    (in-memory for local development and tests, Datastore for the deployed
    App Engine environment) live behind it. Every operation may raise
    :class:`~fablit.application.persistence.PersistenceError` so a storage
    failure is explicit and never reported as a successful publication.
    """

    @abstractmethod
    def save(self, record: PublishedPractice) -> PublishedPractice:
        """Persist a publication record under its stable activity identity.

        Saving a record whose activity identity already exists replaces it in
        place (the SPEC-035 §8 replacement policy), so repeating a publish
        request never creates a duplicate catalogue entry.
        """

    @abstractmethod
    def get(self, activity_id: UUID) -> PublishedPractice | None:
        """Return one publication record by its learner-facing activity identity."""

    @abstractmethod
    def find_by_candidate(self, candidate_id: UUID) -> PublishedPractice | None:
        """Return the publication record sourced from the given candidate, if any."""

    @abstractmethod
    def list_records(self) -> tuple[PublishedPractice, ...]:
        """Return every publication record in deterministic catalogue order.

        Records are ordered by catalogue position, then publication time,
        then the stable activity identity. Position is an advisory ordering
        hint allocated by the publishing instance: concurrently published
        *different* candidates may receive the same position, and the
        deterministic tie-break makes that collision harmless rather than
        requiring atomic cross-instance position allocation (issue #144).
        """

    def visible(self) -> tuple[PublishedPractice, ...]:
        """Return the records learners may discover (published, not withdrawn)."""
        return tuple(record for record in self.list_records() if record.is_visible)


class InMemoryPublishedPracticeStore(PublishedPracticeStore):
    """In-memory publication store for local development and tests.

    Deterministic and side-effect free: publication state lives only in this
    process, so the deployment that needs durable publication uses the
    Datastore adapter instead (SPEC-035 §5, §11).
    """

    def __init__(self) -> None:
        self._records: dict[UUID, PublishedPractice] = {}
        self._lock = Lock()

    def save(self, record: PublishedPractice) -> PublishedPractice:
        with self._lock:
            # Key by candidate_id for uniqueness; also track by activity_id for lookups
            self._records[record.source_candidate_id] = record
            return record

    def get(self, activity_id: UUID) -> PublishedPractice | None:
        with self._lock:
            for record in self._records.values():
                if record.activity_id == activity_id:
                    return record
            return None

    def find_by_candidate(self, candidate_id: UUID) -> PublishedPractice | None:
        with self._lock:
            return self._records.get(candidate_id)

    def list_records(self) -> tuple[PublishedPractice, ...]:
        with self._lock:
            records = tuple(self._records.values())
        # Same deterministic tie-break as the Datastore adapter and the
        # publication port: position, then publication time, then stable
        # activity identity (issue #144).
        return tuple(
            sorted(
                records,
                key=lambda record: (
                    record.activity.activity.position,
                    record.published_at,
                    str(record.activity_id),
                ),
            )
        )


def _validate_position(position: int) -> int:
    if isinstance(position, bool) or not isinstance(position, int) or position < 0:
        raise InvalidPublishedPracticeError(
            "published practice position must be a non-negative integer "
            f"(got {position!r})"
        )
    return position


def _learner_guidance(contract: PracticeContentContract) -> tuple[str, str, str]:
    """Derive the qualitative evaluation guidance for a published practice.

    The learner journey presents three Findings for a completed practice (a
    strength, something to think about, and a next step). Curated practices
    author theirs by hand; a published practice derives them from its own
    approved SPEC-029 contract so the feedback stays grounded in the content
    a human approved. The copy is qualitative only: it never measures,
    ranks, or grades the learner.
    """
    return (
        f"You worked through this practice's task: {contract.task}",
        f"Check your response against what the task asks for: "
        f"{contract.response_contract}",
        f"Take another pass with the purpose in mind: {contract.purpose}",
    )


def _candidate_capability(candidate: PublishableCandidate) -> str:
    """Read the content-design lens from either candidate brief representation."""
    brief = getattr(candidate, "brief", None)
    lens = getattr(brief, "primary_creative_thinking_lens", None) or getattr(
        brief, "primary_capability", None
    )
    return lens if isinstance(lens, str) else ""


def build_published_activity(
    candidate: PublishableCandidate,
    contract: PracticeContentContract,
    *,
    activity_id: UUID,
    position: int,
    published_at: datetime,
) -> DemoActivity:
    """Represent approved candidate content as the existing learner activity.

    Publication reuses the learner-facing ``DemoActivity``/``AssessmentActivity``
    pair rather than a parallel practice model (SPEC-035 §7). The activity is
    delivered as a written-response practice because the existing learner
    journey accepts a written response; the candidate's approved contract
    supplies the SPEC-029 content contract the existing practice/content
    contracts expect. The stable ``activity_id`` is supplied by the caller so
    a republished revision keeps the identity learners already know.
    """
    strength, improvement, next_step = _learner_guidance(contract)
    stimulus = candidate.stimulus
    authored_stimulus = (
        stimulus.to_stimulus(activity_id=activity_id, retrieved_at=published_at)
        if stimulus is not None
        else None
    )
    return DemoActivity(
        activity=AssessmentActivity(
            activity_type=ActivityType.WRITTEN_RESPONSE,
            instructions=contract.task.strip(),
            position=position,
            id=activity_id,
            status=ActivityStatus.ACTIVE,
        ),
        title=candidate.title.strip(),
        description=candidate.description.strip(),
        strength=strength,
        improvement=improvement,
        next_step=next_step,
        content_contract=contract,
        primary_capability=_candidate_capability(candidate),
        fallback_image=(stimulus.image_url if stimulus is not None else None),
        fallback_alt=(stimulus.alt_text if stimulus is not None else None),
        authored_stimulus=authored_stimulus,
        supports_sketch_upload=candidate.supports_sketch_upload,
    )


def publish_candidate(
    candidate: PublishableCandidate,
    *,
    store: PublishedPracticeStore,
    position: int,
    now: datetime | None = None,
) -> PublishedPractice:
    """Explicitly publish an approved candidate to the learner library (SPEC-035 §5).

    The publication boundary revalidates both gates before anything is
    written:

    1. **Content** — the candidate still provides a complete, approvable
       SPEC-029/SPEC-030 contract (otherwise
       :class:`CandidateContentNotPublishableError`).
    2. **State** — the candidate is explicitly approved for *this* revision
       (otherwise :class:`CandidateNotPublishableError`). Generated,
       rejected, and edited-but-not-reapproved candidates are refused.

    Repeating the same publish request is idempotent: an already-published,
    still-visible revision returns the existing record unchanged. Publishing a
    new or re-approved revision writes under the candidate's existing
    publication identity, so republishing never duplicates a catalogue entry
    and learners keep a stable activity identity (SPEC-035 §8, §9).

    Args:
        candidate: The authoring candidate crossing the publication boundary.
        store: The publication persistence port.
        position: The learner-facing catalogue position for a first
            publication (existing publications keep their position).
            Positions are advisory ordering hints, not unique invariants:
            concurrently published different candidates may receive the same
            position, which the catalogue resolves with the deterministic
            tie-break documented on
            :meth:`PublishedPracticeStore.list_records`.
        now: Optional clock override for deterministic tests.

    Raises:
        CandidateContentNotPublishableError: Content fails the publication gate.
        CandidateNotPublishableError: The candidate's state forbids publication.
        InvalidPublishedPracticeError: The requested position is invalid.
        PersistenceError: The publication could not be stored — never reported
            as success and never left as a partial publication.
    """
    now = now or datetime.now(UTC)
    position = _validate_position(position)

    try:
        existing = store.find_by_candidate(candidate.id)
    except PersistenceError:
        # A persistence/read failure is not evidence the candidate has never
        # been published; do not assume absence and risk overwriting.
        raise
    except Exception:
        raise
    if (
        existing is not None
        and existing.source_revision == candidate.revision
        and existing.is_visible
    ):
        # Idempotent repeat of the same publish request: same approved
        # revision, already in the library — nothing to write.
        return existing

    contract = candidate.contract
    if not candidate.validation.is_approvable:
        raise CandidateContentNotPublishableError(
            f"candidate {candidate.id} has validation errors and cannot be published: "
            + "; ".join(
                candidate.validation.structural_errors
                + candidate.validation.feedback_errors
            )
        )
    if contract is None:
        raise CandidateContentNotPublishableError(
            f"candidate {candidate.id} does not provide a complete SPEC-029 "
            "practice content contract and cannot be published"
        )
    if not candidate.title.strip() or not candidate.description.strip():
        raise CandidateContentNotPublishableError(
            f"candidate {candidate.id} must provide a learner-facing title and "
            "description before it can be published"
        )
    if not candidate.is_approved:
        raise CandidateNotPublishableError(
            f"candidate {candidate.id} is not approved (status: {candidate.status}); "
            "only an explicitly approved candidate can be published — approve this "
            "revision first"
        )

    if existing is None:
        # Derive a stable activity identity from the candidate to avoid
        # races producing different identities across concurrent publishes.
        activity_id = uuid5(NAMESPACE_DNS, f"fablit.published.{candidate.id}")
        activity_position = position
        published_at = now
    else:
        # Replacement/republish: keep the stable learner-facing identity and
        # catalogue position; a new approved revision is a new publication
        # event, while a repeat of the same revision keeps its original time.
        activity_id = existing.activity_id
        activity_position = existing.activity.activity.position
        published_at = (
            now
            if existing.source_revision != candidate.revision
            else existing.published_at
        )

    record = PublishedPractice(
        activity=build_published_activity(
            candidate,
            contract,
            activity_id=activity_id,
            position=activity_position,
            published_at=published_at,
        ),
        source_candidate_id=candidate.id,
        source_revision=candidate.revision,
        published_at=published_at,
        withdrawn_at=None,
    )
    try:
        store.save(record)
    except Exception:
        # If a concurrent save created a record for this candidate, reload and
        # return the existing canonical record (idempotent under races).
        try:
            existing_after = store.find_by_candidate(candidate.id)
            if existing_after is not None:
                # Prefer the stored canonical record for this candidate.
                if (
                    existing_after.source_revision == candidate.revision
                    and existing_after.is_visible
                ):
                    return existing_after
                if existing_after.source_revision >= candidate.revision:
                    return existing_after
        except Exception:
            pass
        raise
    # After a successful save, reload the canonical stored record so that
    # concurrent publishes return the same persisted identity and state.
    try:
        canonical = store.find_by_candidate(candidate.id)
        if canonical is not None:
            return canonical
    except Exception:
        pass
    return record


def withdraw_publication(
    candidate_id: UUID,
    *,
    store: PublishedPracticeStore,
    now: datetime | None = None,
) -> PublishedPractice:
    """Withdraw a candidate's published practice from learner discovery (SPEC-035 §8).

    The minimal withdrawal policy: the practice stops appearing in learner
    discovery and practice-mode selections, while completed learner history
    stays readable (it is stored independently) and the publication record is
    kept for traceability. Withdrawal is idempotent — withdrawing an already
    withdrawn publication returns it unchanged.

    Args:
        candidate_id: The source candidate whose publication is withdrawn.
        store: The publication persistence port.
        now: Optional clock override for deterministic tests.

    Raises:
        PublishedPracticeNotFoundError: The candidate has never been published.
        PersistenceError: The withdrawal could not be stored.
    """
    record = store.find_by_candidate(candidate_id)
    if record is None:
        raise PublishedPracticeNotFoundError(
            f"candidate {candidate_id} has no published practice to withdraw"
        )
    if record.is_withdrawn:
        return record
    return store.save(
        replace(record, withdrawn_at=now or datetime.now(UTC)),
    )


def load_publications(store: PublishedPracticeStore) -> tuple[PublishedPractice, ...]:
    """Read every publication record, treating an unavailable store as empty.

    SPEC-035 §9/§10: the authoring side must never become a dependency of
    ordinary learner practice, so a store that cannot be read at startup
    (for example an unavailable Datastore) degrades to the seeded library
    instead of failing application assembly. The failure is explicit in the
    logs rather than silent: it never becomes a successful read.
    """
    try:
        return store.list_records()
    except PersistenceError:
        logger.exception(
            "published practice store unavailable; learners see the seeded library only"
        )
        return ()
