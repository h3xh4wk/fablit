"""Practice Content Contract behaviour (SPEC-029 §4, issue #111).

Every curated practice authors its own contract; derivation from the
activity's title, description, and prompt is a documented fallback for
definitions that author none. These tests protect that boundary: an
authored contract is never overwritten by generic text, the fallback
remains identifiable as generic, and a contract with a blank field is
rejected before it can stand in for a practice.
"""

from __future__ import annotations

from typing import Any

import pytest

from fablit.application.demo_data import DemoActivityDefinition
from fablit.application.errors import InvalidContentContractError
from fablit.application.store import DemoActivity, PracticeContentContract
from fablit.domain import ActivityType
from tests.domain.helpers import make_activity

#: A deliberately practice-specific contract used to prove authored
#: content survives construction untouched.
AUTHORED = PracticeContentContract(
    purpose=("Practise reading how light reveals the surface of a single object."),
    task="Describe how light falls across the object, and what it reveals.",
    expected_thinking=(
        "The learner moves from a visible gradient to a statement about the "
        "surface it reveals, rather than naming brightness and stopping."
    ),
    response_contract=(
        "A short observational response naming one lit area and what it "
        "suggests about the surface."
    ),
    evaluation_intent=(
        "Look for a named region of light tied to a reading of the surface "
        "rather than a list of bright and dark areas."
    ),
    feedback_intent=(
        "Feedback should take one observation about the light, explain what "
        "it opened up, and point to one further detail to examine."
    ),
    reflection_intent=(
        "Invite the learner to notice when they first started reading light "
        "as evidence rather than as decoration."
    ),
    continuation_intent=(
        "A natural next step is a practice that turns the same careful "
        "looking into a design possibility."
    ),
)

_TITLE = "Light Study — Reading a Surface"
_DESCRIPTION = "Practise reading a surface through its light."
_PROMPT = "Describe how light falls across the object in the image."


def _definition_kwargs() -> dict[str, Any]:
    """A minimal definition's content fields, without a contract."""
    return {
        "title": _TITLE,
        "description": _DESCRIPTION,
        "activity_type": ActivityType.OBSERVATION,
        "prompt": _PROMPT,
        "skill_names": ("Visual Analysis",),
        "strength": "You read the light across the surface.",
        "improvement": "Name the boundary where light turns to shadow.",
        "next_step": "Find one reflected light and say what it reveals.",
        "primary_capability": "Observe",
    }


def test_authored_contract_is_kept_verbatim_by_a_definition() -> None:
    """An explicit contract is content, not a prompt for re-derivation."""
    definition = DemoActivityDefinition(
        **_definition_kwargs(), content_contract=AUTHORED
    )

    assert definition.content_contract is AUTHORED
    assert definition.contract is AUTHORED
    assert definition.purpose == AUTHORED.purpose
    assert definition.expected_thinking == AUTHORED.expected_thinking
    assert definition.continuation_intent == AUTHORED.continuation_intent


def test_definition_without_a_contract_receives_the_generic_fallback() -> None:
    """A definition that authors no contract still resolves one, generically."""
    definition = DemoActivityDefinition(**_definition_kwargs())

    assert definition.content_contract is None
    assert definition.contract == PracticeContentContract.from_activity(
        title=_TITLE,
        description=_DESCRIPTION,
        prompt=_PROMPT,
        primary_capability="Observe",
    )


def test_authored_contract_is_kept_verbatim_by_the_demo_activity() -> None:
    """The built activity never overwrites the authored contract either."""
    activity = DemoActivity(
        activity=make_activity(instructions=_PROMPT),
        title=_TITLE,
        description=_DESCRIPTION,
        strength="You read the light across the surface.",
        improvement="Name the boundary where light turns to shadow.",
        next_step="Find one reflected light and say what it reveals.",
        content_contract=AUTHORED,
        primary_capability="Observe",
    )

    assert activity.content_contract is AUTHORED
    assert activity.contract is AUTHORED
    assert activity.evaluation_intent == AUTHORED.evaluation_intent


def test_demo_activity_without_a_contract_falls_back_to_generic_text() -> None:
    """The fallback derives from the activity's own content, nothing more."""
    activity = DemoActivity(
        activity=make_activity(instructions=_PROMPT),
        title=_TITLE,
        description=_DESCRIPTION,
        strength="You read the light across the surface.",
        improvement="Name the boundary where light turns to shadow.",
        next_step="Find one reflected light and say what it reveals.",
    )

    assert activity.content_contract is None
    assert activity.contract == PracticeContentContract.from_activity(
        title=_TITLE,
        description=_DESCRIPTION,
        prompt=_PROMPT,
        primary_capability="",
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "purpose",
        "task",
        "expected_thinking",
        "response_contract",
        "evaluation_intent",
        "feedback_intent",
        "reflection_intent",
        "continuation_intent",
    ],
)
def test_contract_rejects_a_blank_field(field_name: str) -> None:
    """SPEC-029 §4: a contract field that says nothing is not a contract."""
    values: dict[str, str] = {
        "purpose": "What the practice deliberately exercises.",
        "task": "What the learner is asked to do.",
        "expected_thinking": "The reasoning behaviour the task elicits.",
        "response_contract": "The form a useful response takes.",
        "evaluation_intent": "What a useful evaluation should look for.",
        "feedback_intent": "What feedback should help the learner understand.",
        "reflection_intent": "What the learner is invited to notice.",
        "continuation_intent": "What practice would naturally follow.",
    }
    values[field_name] = "   "

    with pytest.raises(InvalidContentContractError, match=field_name):
        PracticeContentContract(**values)


def test_generic_derivation_cannot_build_a_contract_from_nothing() -> None:
    """Even the fallback refuses to ship a contract with blank content."""
    with pytest.raises(InvalidContentContractError):
        PracticeContentContract.from_activity(
            title="",
            description="",
            prompt="",
            primary_capability="",
        )
