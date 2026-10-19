"""Presentation helpers for learner-facing task text.

Authoring candidates are written by a model, so their ``task`` can be several
sentences long. The practice page emphasises the actionable opening sentence
and shows the rest as ordinary body text, which keeps the whole task out of
display type. This is a presentation concern, so the saved contract text is
left untouched.
"""

from __future__ import annotations

import re

#: Emphasis markers a generated task may carry even though it is plain text.
_EMPHASIS = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")

#: The end of the opening sentence: terminal punctuation followed by space.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_task_text(text: str) -> tuple[str, str]:
    """Split task text into its opening sentence and the supporting detail.

    Args:
        text: The saved task text, possibly spanning several sentences or
            lines with leftover markdown emphasis.

    Returns:
        ``(lead, detail)``. The lead is the first sentence (or the first line
        when the text has no sentence punctuation); the detail is everything
        after it, or an empty string when there is nothing more to show.
    """
    cleaned = _EMPHASIS.sub(lambda match: match.group(1) or match.group(2), text)
    cleaned = "\n".join(
        " ".join(line.split()) for line in cleaned.strip().splitlines()
    ).strip()
    if not cleaned:
        return "", ""

    sentence_end = _SENTENCE_END.search(cleaned)
    if sentence_end is not None:
        lead = cleaned[: sentence_end.start()].strip()
        detail = cleaned[sentence_end.end() :].strip()
        if lead:
            return lead, detail

    lead, _, detail = cleaned.partition("\n")
    return lead.strip(), detail.strip()
