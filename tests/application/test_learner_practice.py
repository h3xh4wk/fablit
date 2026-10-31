"""Application tests for SPEC-044 learner-requested private practice.

The workflow under test is the bounded generation path: validate the learner's
request, optionally add a minimal slice of that learner's own history, generate
through a provider-neutral port, validate the untrusted output against the
existing SPEC-029/SPEC-030 boundary, and persist the result privately.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from typing import Any
from uuid import UUID, uuid4

import pytest

from fablit.application import (
    DEFAULT_LEARNER_PRACTICE_RATE_LIMIT,
    DEFAULT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS,
    DEMO_LEARNER_ID,
    FORBIDDEN_FEEDBACK_TERMS,
    RATE_LIMIT_MESSAGE,
    ChallengePreference,
    DemoActivity,
    DemoEvaluator,
    FakeLearnerPracticeGenerator,
    GeneratedPracticeRecord,
    GeneratedPracticeRepository,
    GeneratedPracticeValidationError,
    HistoryContext,
    InMemoryGeneratedPracticeRepository,
    InvalidLearnerPracticeRequestError,
    LearnerJourneyStore,
    LearnerPracticeGenerationError,
    LearnerPracticeGenerationRequest,
    LearnerPracticeRateLimitError,
    PracticeApplication,
    PracticeArea,
    PracticeRequest,
    build_demo_activities,
    build_demo_activity_map,
    build_demo_skills,
    build_generated_activity,
    build_stimulus_provider,
    default_candidate_data,
    generate_private_practice,
    practice_id_for,
    rate_limit_message,
)
from fablit.application.persistence import (
    PersistenceError,
    PracticeHistoryRepository,
    PracticeHistorySummary,
)
from fablit.application.repositories import InMemoryPracticeHistoryRepository

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)


def _request(**overrides: Any) -> PracticeRequest:
    values: dict[str, Any] = {
        "learner_id": DEMO_LEARNER_ID,
        "text": "I want to practise noticing how colour and texture work together.",
        "area": PracticeArea.VISUAL_ANALYSIS,
        "response_form": "A short written response",
        "challenge": ChallengePreference.FAMILIAR,
        "include_history": False,
        "created_at": NOW,
        "token": uuid4(),
    }
    values.update(overrides)
    return PracticeRequest(**values)


def _candidate_data(**overrides: Any) -> dict[str, Any]:
    request = LearnerPracticeGenerationRequest(
        request=_request(), history=HistoryContext()
    )
    data = default_candidate_data(request)
    data.update(overrides)
    return data


# --- Request validation ------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"text": "   "}, "Write what you would like to practise."),
        (
            {"text": "a" * 601},
            "Keep your request to 600 characters or fewer.",
        ),
        ({"area": "visual-analysis"}, "Choose a supported practice area"),
        ({"challenge": "gentle"}, "Choose a supported challenge preference"),
        (
            {"response_form": "  "},
            "Choose the kind of response you want to make.",
        ),
        (
            {"examination_context": "   "},
            "Examination context must be non-blank when provided.",
        ),
        (
            {"examination_context": "a" * 201},
            "Keep the examination context to 200 characters or fewer.",
        ),
        ({"created_at": "2026-10-30"}, "must record when it was made"),
        ({"token": "not-a-uuid"}, "practice request token must be a UUID"),
        ({"learner_id": "learner"}, "learner identity must be a UUID"),
        ({"include_history": "yes"}, "include_history must be a boolean"),
    ],
)
def test_invalid_requests_are_refused_with_actionable_copy(
    overrides: dict[str, Any], message: str
) -> None:
    with pytest.raises(InvalidLearnerPracticeRequestError) as caught:
        _request(**overrides)

    assert message in str(caught.value)


def test_request_timestamp_must_be_timezone_aware() -> None:
    with pytest.raises(InvalidLearnerPracticeRequestError):
        _request(created_at=datetime(2026, 10, 30, 12, 0))


def test_practice_request_defaults_include_history_to_false() -> None:
    request = PracticeRequest(
        learner_id=DEMO_LEARNER_ID,
        text="I want to practise noticing how colour and texture work together.",
        area=PracticeArea.VISUAL_ANALYSIS,
        response_form="A short written response",
        challenge=ChallengePreference.FAMILIAR,
    )

    assert request.include_history is False


def test_history_context_is_bounded() -> None:
    HistoryContext(
        recent_titles=("A practice",),
        recent_areas=("Observe",),
    )

    with pytest.raises(InvalidLearnerPracticeRequestError):
        HistoryContext(recent_titles=tuple(f"Practice {i}" for i in range(6)))

    with pytest.raises(InvalidLearnerPracticeRequestError):
        HistoryContext(recent_titles=("  ",))


def test_an_empty_history_context_is_recognised() -> None:
    assert HistoryContext().is_empty
    assert not HistoryContext(recent_titles=("A practice",)).is_empty


# --- Generation --------------------------------------------------------------


def test_generation_persists_a_validated_private_practice() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    generator = FakeLearnerPracticeGenerator()
    request = _request()

    record = generate_private_practice(
        repository,
        generator,
        request=request,
        history=HistoryContext(),
        now=NOW,
    )

    assert len(generator.calls) == 1
    assert record.learner_id == DEMO_LEARNER_ID
    assert record.request_token == request.token
    assert record.practice_id == practice_id_for(DEMO_LEARNER_ID, request.token)
    assert record.area is PracticeArea.VISUAL_ANALYSIS
    assert record.challenge is ChallengePreference.FAMILIAR
    assert record.response_form == "A short written response"
    assert record.provider == "fake-learner-generator"
    assert record.model == "fake-model"
    assert record.used_history is False
    assert record.contract.task
    assert repository.get(DEMO_LEARNER_ID, record.practice_id) == record


def test_a_retried_request_reuses_the_persisted_practice() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    generator = FakeLearnerPracticeGenerator()
    request = _request()

    first = generate_private_practice(
        repository, generator, request=request, history=HistoryContext()
    )
    second = generate_private_practice(
        repository, generator, request=request, history=HistoryContext()
    )

    assert second == first
    assert len(generator.calls) == 1
    assert len(repository.list_for_learner(DEMO_LEARNER_ID)) == 1


def test_invalid_provider_output_never_reaches_the_learner() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    data = _candidate_data()
    contract = dict(data["contract"])
    contract["task"] = ""
    data["contract"] = contract
    generator = FakeLearnerPracticeGenerator(data)

    with pytest.raises(GeneratedPracticeValidationError) as caught:
        generate_private_practice(
            repository,
            generator,
            request=_request(),
            history=HistoryContext(),
        )

    assert "couldn't make a practice from that request" in str(caught.value)
    assert repository.list_for_learner(DEMO_LEARNER_ID) == ()


def test_an_empty_provider_title_is_refused() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    generator = FakeLearnerPracticeGenerator(_candidate_data(title="   "))

    with pytest.raises(GeneratedPracticeValidationError):
        generate_private_practice(
            repository,
            generator,
            request=_request(),
            history=HistoryContext(),
        )


def test_a_generation_failure_is_reported_without_leaking_details() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    generator = FakeLearnerPracticeGenerator(
        error=RuntimeError("upstream detail: api-key-secret")
    )

    with pytest.raises(LearnerPracticeGenerationError) as caught:
        generate_private_practice(
            repository,
            generator,
            request=_request(),
            history=HistoryContext(),
        )

    assert "temporarily unavailable" in str(caught.value)
    assert "api-key-secret" not in str(caught.value)
    assert repository.list_for_learner(DEMO_LEARNER_ID) == ()


def test_a_provider_generation_error_is_passed_through() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    generator = FakeLearnerPracticeGenerator(
        error=LearnerPracticeGenerationError("the practice generator is unavailable")
    )

    with pytest.raises(LearnerPracticeGenerationError) as caught:
        generate_private_practice(
            repository,
            generator,
            request=_request(),
            history=HistoryContext(),
        )

    assert str(caught.value) == "the practice generator is unavailable"


def test_persistence_failure_is_not_reported_as_success() -> None:
    class FailingRepository(GeneratedPracticeRepository):
        def save(self, record: GeneratedPracticeRecord) -> GeneratedPracticeRecord:
            raise PersistenceError("simulated outage")

        def get(
            self, learner_id: UUID, practice_id: UUID
        ) -> GeneratedPracticeRecord | None:
            return None

        def list_for_learner(
            self, learner_id: UUID
        ) -> tuple[GeneratedPracticeRecord, ...]:
            return ()

    with pytest.raises(PersistenceError):
        generate_private_practice(
            FailingRepository(),
            FakeLearnerPracticeGenerator(),
            request=_request(),
            history=HistoryContext(),
        )


def test_history_context_is_opt_in_and_never_carries_learner_identity() -> None:
    generator = FakeLearnerPracticeGenerator()
    history = HistoryContext(
        recent_titles=("Reading Composition",),
        recent_areas=("Observe",),
    )

    record = generate_private_practice(
        InMemoryGeneratedPracticeRepository(),
        generator,
        request=_request(include_history=True),
        history=history,
    )

    sent = generator.calls[0]
    payload = sent.as_payload()
    assert payload["history"] == {
        "recent_titles": ["Reading Composition"],
        "recent_areas": ["Observe"],
    }
    assert str(DEMO_LEARNER_ID) not in str(payload)
    assert record.used_history is True


def test_history_context_is_absent_when_the_learner_opts_out() -> None:
    generator = FakeLearnerPracticeGenerator()
    history = HistoryContext(
        recent_titles=("Reading Composition",),
        recent_areas=("Observe",),
    )

    record = generate_private_practice(
        InMemoryGeneratedPracticeRepository(),
        generator,
        request=_request(include_history=False),
        history=history,
    )

    sent = generator.calls[0]
    assert sent.history.is_empty
    assert sent.as_payload()["history"] == {
        "recent_titles": [],
        "recent_areas": [],
    }
    assert record.used_history is False


def test_examination_context_is_carried_when_the_learner_states_it() -> None:
    record = generate_private_practice(
        InMemoryGeneratedPracticeRepository(),
        FakeLearnerPracticeGenerator(),
        request=_request(examination_context="A portfolio interview next month"),
        history=HistoryContext(),
    )

    assert record.examination_context == "A portfolio interview next month"


# --- Rate limiting -----------------------------------------------------------


def test_rate_limit_blocks_excess_requests_and_suppresses_provider_calls() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    generator = FakeLearnerPracticeGenerator()

    for index in range(DEFAULT_LEARNER_PRACTICE_RATE_LIMIT):
        generate_private_practice(
            repository,
            generator,
            request=_request(token=uuid4()),
            history=HistoryContext(),
            now=NOW + timedelta(minutes=index),
        )

    assert len(generator.calls) == DEFAULT_LEARNER_PRACTICE_RATE_LIMIT

    with pytest.raises(LearnerPracticeRateLimitError) as caught:
        generate_private_practice(
            repository,
            generator,
            request=_request(token=uuid4()),
            history=HistoryContext(),
            now=NOW + timedelta(minutes=10),
        )

    assert len(generator.calls) == DEFAULT_LEARNER_PRACTICE_RATE_LIMIT
    assert caught.value.retry_after_seconds == 3000
    assert "reached the limit of 5 practice requests per hour" in str(caught.value)
    assert "try again in 50 minutes" in str(caught.value)
    lowered = str(caught.value).lower()
    for term in FORBIDDEN_FEEDBACK_TERMS:
        assert term not in lowered


def test_rate_limit_boundary_expires_after_configured_window() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    generator = FakeLearnerPracticeGenerator()
    window = DEFAULT_LEARNER_PRACTICE_RATE_WINDOW_SECONDS

    generate_private_practice(
        repository,
        generator,
        request=_request(token=uuid4()),
        history=HistoryContext(),
        now=NOW,
        rate_limit=2,
        rate_window_seconds=window,
    )
    generate_private_practice(
        repository,
        generator,
        request=_request(token=uuid4()),
        history=HistoryContext(),
        now=NOW + timedelta(seconds=600),
        rate_limit=2,
        rate_window_seconds=window,
    )

    # One second before the oldest request exits the window: still rate-limited.
    with pytest.raises(LearnerPracticeRateLimitError) as caught:
        generate_private_practice(
            repository,
            generator,
            request=_request(token=uuid4()),
            history=HistoryContext(),
            now=NOW + timedelta(seconds=window - 1),
            rate_limit=2,
            rate_window_seconds=window,
        )

    assert caught.value.retry_after_seconds == 1
    assert len(generator.calls) == 2

    # At the window boundary: the first slot has expired and a new request succeeds.
    record = generate_private_practice(
        repository,
        generator,
        request=_request(token=uuid4()),
        history=HistoryContext(),
        now=NOW + timedelta(seconds=window),
        rate_limit=2,
        rate_window_seconds=window,
    )

    assert record.practice_id is not None
    assert len(generator.calls) == 3


def test_idempotent_resubmission_succeeds_even_when_learner_is_at_rate_limit() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    generator = FakeLearnerPracticeGenerator()
    first_request = _request(token=uuid4())
    second_request = _request(token=uuid4())

    first = generate_private_practice(
        repository,
        generator,
        request=first_request,
        history=HistoryContext(),
        now=NOW,
        rate_limit=2,
    )
    second = generate_private_practice(
        repository,
        generator,
        request=second_request,
        history=HistoryContext(),
        now=NOW + timedelta(minutes=1),
        rate_limit=2,
    )

    # Repeating an already-generated token returns the existing record without
    # invoking the provider or failing with a rate-limit error.
    repeated_first = generate_private_practice(
        repository,
        generator,
        request=first_request,
        history=HistoryContext(),
        now=NOW + timedelta(minutes=2),
        rate_limit=2,
    )
    repeated_second = generate_private_practice(
        repository,
        generator,
        request=second_request,
        history=HistoryContext(),
        now=NOW + timedelta(minutes=2),
        rate_limit=2,
    )

    assert repeated_first == first
    assert repeated_second == second
    assert len(generator.calls) == 2


def test_failed_provider_calls_still_count_toward_the_rate_limit() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    failing_generator = FakeLearnerPracticeGenerator(
        error=LearnerPracticeGenerationError("provider temporary failure")
    )

    for index in range(2):
        with pytest.raises(LearnerPracticeGenerationError):
            generate_private_practice(
                repository,
                failing_generator,
                request=_request(token=uuid4()),
                history=HistoryContext(),
                now=NOW + timedelta(seconds=index * 10),
                rate_limit=2,
            )

    assert len(failing_generator.calls) == 2

    with pytest.raises(LearnerPracticeRateLimitError):
        generate_private_practice(
            repository,
            failing_generator,
            request=_request(token=uuid4()),
            history=HistoryContext(),
            now=NOW + timedelta(seconds=30),
            rate_limit=2,
        )

    assert len(failing_generator.calls) == 2


def test_rate_limit_is_scoped_per_learner_identity() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    generator = FakeLearnerPracticeGenerator()
    other_learner = uuid4()

    generate_private_practice(
        repository,
        generator,
        request=_request(learner_id=DEMO_LEARNER_ID, token=uuid4()),
        history=HistoryContext(),
        now=NOW,
        rate_limit=1,
    )

    with pytest.raises(LearnerPracticeRateLimitError):
        generate_private_practice(
            repository,
            generator,
            request=_request(learner_id=DEMO_LEARNER_ID, token=uuid4()),
            history=HistoryContext(),
            now=NOW + timedelta(minutes=1),
            rate_limit=1,
        )

    other_record = generate_private_practice(
        repository,
        generator,
        request=_request(learner_id=other_learner, token=uuid4()),
        history=HistoryContext(),
        now=NOW + timedelta(minutes=1),
        rate_limit=1,
    )

    assert other_record.learner_id == other_learner
    assert len(generator.calls) == 2


def test_rate_limit_message_formats_custom_windows_and_waits_cleanly() -> None:
    assert "5 practice requests per hour" in RATE_LIMIT_MESSAGE
    assert "1 practice request per minute" in rate_limit_message(
        limit=1, window_seconds=60, retry_after_seconds=60
    )
    assert "per 2 hours" in rate_limit_message(
        limit=3, window_seconds=7200, retry_after_seconds=90
    )
    assert "per 15 minutes" in rate_limit_message(
        limit=2, window_seconds=900, retry_after_seconds=1
    )
    assert "try again in 1 second." in rate_limit_message(
        limit=2, window_seconds=30, retry_after_seconds=1
    )
    assert "per second" in rate_limit_message(
        limit=1, window_seconds=1, retry_after_seconds=5
    )


def test_reserve_generation_slot_validates_parameters_and_base_fallback() -> None:
    repository = InMemoryGeneratedPracticeRepository()

    with pytest.raises(ValueError, match="learner_id"):
        repository.reserve_generation_slot(
            "not-a-uuid",  # type: ignore[arg-type]
            now=NOW,
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        repository.reserve_generation_slot(
            DEMO_LEARNER_ID,
            now=datetime(2026, 10, 30, 12, 0),
        )
    with pytest.raises(ValueError, match="rate limit must be"):
        repository.reserve_generation_slot(DEMO_LEARNER_ID, now=NOW, limit=0)
    with pytest.raises(ValueError, match="window_seconds"):
        repository.reserve_generation_slot(DEMO_LEARNER_ID, now=NOW, window_seconds=0)

    record = generate_private_practice(
        InMemoryGeneratedPracticeRepository(),
        FakeLearnerPracticeGenerator(),
        request=_request(),
        history=HistoryContext(),
        now=NOW,
    )

    class CustomRepository(GeneratedPracticeRepository):
        def save(self, item: GeneratedPracticeRecord) -> GeneratedPracticeRecord:
            return item

        def get(
            self, learner_id: UUID, practice_id: UUID
        ) -> GeneratedPracticeRecord | None:
            return None

        def list_for_learner(
            self, learner_id: UUID
        ) -> tuple[GeneratedPracticeRecord, ...]:
            return (record,)

    custom = CustomRepository()
    with pytest.raises(ValueError, match="learner_id"):
        custom.reserve_generation_slot("bad", now=NOW)  # type: ignore[arg-type]
    assert custom.reserve_generation_slot(DEMO_LEARNER_ID, now=NOW, limit=2) is None
    assert (
        custom.reserve_generation_slot(
            DEMO_LEARNER_ID,
            now=NOW + timedelta(seconds=10),
            limit=1,
            window_seconds=60,
        )
        == 50
    )


# --- Private storage ---------------------------------------------------------


def test_another_learner_cannot_read_a_generated_practice() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    record = generate_private_practice(
        repository,
        FakeLearnerPracticeGenerator(),
        request=_request(),
        history=HistoryContext(),
    )

    assert repository.get(uuid4(), record.practice_id) is None
    assert repository.list_for_learner(uuid4()) == ()


def test_requested_practices_are_listed_newest_first_for_their_learner() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    older = generate_private_practice(
        repository,
        FakeLearnerPracticeGenerator(),
        request=_request(created_at=NOW),
        history=HistoryContext(),
        now=NOW,
    )
    newer = generate_private_practice(
        repository,
        FakeLearnerPracticeGenerator(),
        request=_request(),
        history=HistoryContext(),
        now=datetime(2026, 10, 31, 9, 0, tzinfo=UTC),
    )

    listed = repository.list_for_learner(DEMO_LEARNER_ID)

    assert listed == (newer, older)
    assert repository.list_for_learner(uuid4()) == ()


def test_a_repository_refuses_non_record_values() -> None:
    repository = InMemoryGeneratedPracticeRepository()

    with pytest.raises(ValueError):
        repository.save("not a record")  # type: ignore[arg-type]


# --- Learner activity representation ----------------------------------------


def test_a_generated_practice_reuses_the_learner_activity_representation() -> None:
    record = generate_private_practice(
        InMemoryGeneratedPracticeRepository(),
        FakeLearnerPracticeGenerator(),
        request=_request(),
        history=HistoryContext(),
    )

    activity = build_generated_activity(record)

    assert activity.activity.id == record.practice_id
    assert activity.title == record.title
    assert activity.activity.instructions == record.contract.task
    assert activity.content_contract == record.contract


# --- Practice application integration ---------------------------------------


def _application(
    *,
    generated: tuple[GeneratedPracticeRecord, ...] = (),
    history: PracticeHistoryRepository | None = None,
) -> tuple[PracticeApplication, tuple[DemoActivity, ...]]:
    """Build an application with the activities it was actually seeded with."""
    activities = build_demo_activities()
    application = PracticeApplication(
        store=LearnerJourneyStore(
            learner_id=DEMO_LEARNER_ID,
            activities=activities,
            skills=build_demo_skills(),
        ),
        evaluator=DemoEvaluator(build_demo_activity_map(activities)),
        stimulus_provider=build_stimulus_provider(activities, provider_name="builtin"),
        history_repository=history,
        generated_practices=generated,
    )
    return application, activities


def test_generated_practices_stay_out_of_shared_discovery() -> None:
    record = generate_private_practice(
        InMemoryGeneratedPracticeRepository(),
        FakeLearnerPracticeGenerator(),
        request=_request(),
        history=HistoryContext(),
    )
    application, _ = _application(generated=(record,))

    dashboard_ids = {activity.id for activity in application.get_dashboard().activities}
    requested = application.get_requested_practices()

    assert record.practice_id not in dashboard_ids
    assert [item.practice_id for item in requested] == [record.practice_id]


def test_the_preview_shows_the_validated_brief() -> None:
    record = generate_private_practice(
        InMemoryGeneratedPracticeRepository(),
        FakeLearnerPracticeGenerator(),
        request=_request(examination_context="A portfolio interview next month"),
        history=HistoryContext(),
    )
    application, _ = _application(generated=(record,))

    preview = application.get_generated_practice_preview(record.practice_id)

    assert preview is not None
    assert preview.title == record.title
    assert preview.task == record.contract.task
    assert preview.area_label == "Visual analysis"
    assert preview.challenge_label == "Familiar"
    assert preview.examination_context == "A portfolio interview next month"
    assert preview.is_completed is False
    assert application.get_generated_practice_preview(uuid4()) is None


def test_registering_a_new_practice_makes_it_available_immediately() -> None:
    application, _ = _application()
    record = generate_private_practice(
        InMemoryGeneratedPracticeRepository(),
        FakeLearnerPracticeGenerator(),
        request=_request(),
        history=HistoryContext(),
    )

    application.register_generated_practice(record)

    assert [item.practice_id for item in application.get_requested_practices()] == [
        record.practice_id
    ]
    assert application.get_generated_practice_preview(record.practice_id) is not None


def test_re_applying_the_same_practices_is_a_no_op() -> None:
    record = generate_private_practice(
        InMemoryGeneratedPracticeRepository(),
        FakeLearnerPracticeGenerator(),
        request=_request(),
        history=HistoryContext(),
    )
    application, _ = _application(generated=(record,))

    application.apply_generated_practices((record,))

    assert len(application.get_requested_practices()) == 1


class _HistoryRepo(InMemoryPracticeHistoryRepository):
    """History double with a settable summary list for context tests."""

    def __init__(self) -> None:
        super().__init__()
        self.summaries: tuple[PracticeHistorySummary, ...] = ()

    def list_completions(self, learner_id: UUID) -> tuple[PracticeHistorySummary, ...]:
        return self.summaries

    def has_completed_activity(self, learner_id: UUID, activity_id: UUID) -> bool:
        return any(summary.activity_id == activity_id for summary in self.summaries)


def _summary(activity_id: UUID, title: str) -> PracticeHistorySummary:
    return PracticeHistorySummary(
        completion_id=uuid4(),
        activity_id=activity_id,
        activity_title=title,
        completed_at=NOW,
        submission_preview="A response preview.",
    )


def test_history_context_uses_only_the_learners_own_recent_practice() -> None:
    history = _HistoryRepo()
    application, activities = _application(history=history)
    first, second = activities[0], activities[1]
    history.summaries = (
        _summary(first.activity.id, "First practice"),
        _summary(second.activity.id, "Second practice"),
    )

    context = application.get_history_context()

    assert context.recent_titles == ("First practice", "Second practice")
    assert context.recent_areas == (
        first.primary_capability,
        second.primary_capability,
    )
    assert len(context.recent_titles) <= 5


def test_history_context_is_bounded_to_five_items() -> None:
    history = _HistoryRepo()
    application, activities = _application(history=history)
    history.summaries = tuple(
        _summary(activities[index % len(activities)].activity.id, f"Practice {index}")
        for index in range(9)
    )

    context = application.get_history_context()

    assert context.recent_titles == tuple(f"Practice {index}" for index in range(5))


def test_an_unavailable_history_store_degrades_to_no_context() -> None:
    class FailingHistory(_HistoryRepo):
        def list_completions(
            self, learner_id: UUID
        ) -> tuple[PracticeHistorySummary, ...]:
            raise PersistenceError("simulated outage")

    application, _ = _application(history=FailingHistory())

    assert application.get_history_context().is_empty


def test_no_history_repository_means_no_context() -> None:
    application, _ = _application()

    assert application.get_history_context().is_empty


def test_a_completed_generated_practice_is_marked_practised() -> None:
    record = generate_private_practice(
        InMemoryGeneratedPracticeRepository(),
        FakeLearnerPracticeGenerator(),
        request=_request(),
        history=HistoryContext(),
    )
    history = _HistoryRepo()
    application, _ = _application(
        generated=(record,),
        history=history,
    )
    history.summaries = (_summary(record.practice_id, record.title),)

    summary = application.get_requested_practices()[0]
    preview = application.get_generated_practice_preview(record.practice_id)

    assert summary.is_completed is True
    assert preview is not None and preview.is_completed is True


def test_concurrent_duplicate_requests_claim_once_and_share_the_result() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    entered_provider = Event()
    release_provider = Event()

    class CoordinatedGenerator(FakeLearnerPracticeGenerator):
        def generate(self, request: LearnerPracticeGenerationRequest) -> Any:
            entered_provider.set()
            release_provider.wait(timeout=2.0)
            return super().generate(request)

    generator = CoordinatedGenerator()
    token = uuid4()
    first_request = _request(token=token, text="First phrasing")
    second_request = _request(token=token, text="Duplicate submission phrasing")

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(
            generate_private_practice,
            repository,
            generator,
            request=first_request,
            history=HistoryContext(),
            now=NOW,
            rate_limit=1,
            rate_window_seconds=3600,
        )
        assert entered_provider.wait(timeout=2.0)
        second_future = pool.submit(
            generate_private_practice,
            repository,
            generator,
            request=second_request,
            history=HistoryContext(),
            now=NOW + timedelta(seconds=1),
            rate_limit=1,
            rate_window_seconds=3600,
        )
        # Allow the duplicate thread to enter claim_generation / await_generation
        # before the provider finishes.
        release_provider.wait(timeout=0.02)
        release_provider.set()
        first_record = first_future.result(timeout=2.0)
        second_record = second_future.result(timeout=2.0)

    assert first_record == second_record
    assert len(generator.calls) == 1
    assert repository.list_for_learner(DEMO_LEARNER_ID) == (first_record,)


def test_concurrent_duplicate_failure_calls_provider_once_and_releases_claim() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    entered_provider = Event()
    release_provider = Event()

    class FailingCoordinatedGenerator(FakeLearnerPracticeGenerator):
        def generate(self, request: LearnerPracticeGenerationRequest) -> Any:
            self.calls.append(request)
            entered_provider.set()
            release_provider.wait(timeout=2.0)
            raise RuntimeError("provider timeout")

    failing_generator = FailingCoordinatedGenerator()
    request = _request(token=uuid4())

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(
            generate_private_practice,
            repository,
            failing_generator,
            request=request,
            history=HistoryContext(),
            now=NOW,
        )
        assert entered_provider.wait(timeout=2.0)
        second_future = pool.submit(
            generate_private_practice,
            repository,
            failing_generator,
            request=request,
            history=HistoryContext(),
            now=NOW,
        )
        release_provider.wait(timeout=0.02)
        release_provider.set()

        with pytest.raises(LearnerPracticeGenerationError):
            first_future.result(timeout=2.0)
        with pytest.raises(LearnerPracticeGenerationError):
            second_future.result(timeout=2.0)

    assert len(failing_generator.calls) == 1

    # Because the claim was released on failure, an explicit retry succeeds.
    working_generator = FakeLearnerPracticeGenerator()
    recovered = generate_private_practice(
        repository,
        working_generator,
        request=request,
        history=HistoryContext(),
        now=NOW + timedelta(seconds=5),
    )
    assert len(working_generator.calls) == 1
    assert repository.get(DEMO_LEARNER_ID, recovered.practice_id) == recovered


def test_in_memory_claim_expiry_and_ownership_checks() -> None:
    repository = InMemoryGeneratedPracticeRepository()
    other_learner = uuid4()
    practice_id = uuid4()

    outcome = repository.claim_generation(
        DEMO_LEARNER_ID, practice_id, now=NOW, ttl_seconds=30
    )
    assert outcome.claimed is True
    assert outcome.existing is None

    # Active claim for same learner returns claimed=False.
    duplicate = repository.claim_generation(
        DEMO_LEARNER_ID,
        practice_id,
        now=NOW + timedelta(seconds=10),
        ttl_seconds=30,
    )
    assert duplicate.claimed is False
    assert duplicate.existing is None

    # Another learner cannot claim or save or await the same practice_id.
    with pytest.raises(PersistenceError, match="belongs to another learner"):
        repository.claim_generation(
            other_learner,
            practice_id,
            now=NOW + timedelta(seconds=10),
            ttl_seconds=30,
        )
    with pytest.raises(PersistenceError, match="belongs to another learner"):
        repository.await_generation(other_learner, practice_id, timeout_seconds=0.01)

    record = generate_private_practice(
        InMemoryGeneratedPracticeRepository(),
        FakeLearnerPracticeGenerator(),
        request=_request(learner_id=other_learner),
        history=HistoryContext(),
        now=NOW,
    )
    colliding_record = GeneratedPracticeRecord(
        practice_id=practice_id,
        learner_id=other_learner,
        request_token=record.request_token,
        title=record.title,
        description=record.description,
        contract=record.contract,
        area=record.area,
        challenge=record.challenge,
        response_form=record.response_form,
        primary_capability=record.primary_capability,
        used_history=record.used_history,
        provider=record.provider,
        model=record.model,
        generated_at=record.generated_at,
        created_at=record.created_at,
    )
    with pytest.raises(PersistenceError, match="belongs to another learner"):
        repository.save(colliding_record)

    # Once the lease expires, the same learner can reclaim it.
    reclaimed = repository.claim_generation(
        DEMO_LEARNER_ID,
        practice_id,
        now=NOW + timedelta(seconds=31),
        ttl_seconds=30,
    )
    assert reclaimed.claimed is True

    own_record = GeneratedPracticeRecord(
        practice_id=practice_id,
        learner_id=DEMO_LEARNER_ID,
        request_token=record.request_token,
        title=record.title,
        description=record.description,
        contract=record.contract,
        area=record.area,
        challenge=record.challenge,
        response_form=record.response_form,
        primary_capability=record.primary_capability,
        used_history=record.used_history,
        provider=record.provider,
        model=record.model,
        generated_at=record.generated_at,
        created_at=record.created_at,
    )
    repository.save(own_record)
    with pytest.raises(PersistenceError, match="belongs to another learner"):
        repository.save(colliding_record)
    with pytest.raises(PersistenceError, match="belongs to another learner"):
        repository.claim_generation(other_learner, practice_id, now=NOW)
    with pytest.raises(PersistenceError, match="belongs to another learner"):
        repository.await_generation(other_learner, practice_id, timeout_seconds=0.01)
