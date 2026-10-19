"""Unit tests for splitting saved task text into a lead and detail."""

from __future__ import annotations

import pytest

from app.task_text import split_task_text


def test_single_sentence_has_no_detail() -> None:
    assert split_task_text("Describe what is visible.") == (
        "Describe what is visible.",
        "",
    )


def test_following_sentences_become_the_detail() -> None:
    assert split_task_text(
        "Analyse the image. Name three details. Explain how they guide attention."
    ) == (
        "Analyse the image.",
        "Name three details. Explain how they guide attention.",
    )


def test_markdown_emphasis_is_removed_before_splitting() -> None:
    assert split_task_text("**Analyse the image.** Then explain your reading.") == (
        "Analyse the image.",
        "Then explain your reading.",
    )


def test_a_line_break_separates_the_lead_when_there_is_no_punctuation() -> None:
    assert split_task_text("Read the prompt\nThen write one paragraph.") == (
        "Read the prompt",
        "Then write one paragraph.",
    )


def test_line_breaks_inside_the_detail_are_preserved() -> None:
    assert split_task_text("Do this. First line.\nSecond line.") == (
        "Do this.",
        "First line.\nSecond line.",
    )


@pytest.mark.parametrize("text", ["", "   ", "\n\n"])
def test_blank_text_has_no_parts(text: str) -> None:
    assert split_task_text(text) == ("", "")
