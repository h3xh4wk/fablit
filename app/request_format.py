"""Response-format negotiation for the web layer.

A browser navigation sends ``Accept: text/html``, but htmx — which boosts
every form and link in the layout — submits over ``XMLHttpRequest``, where the
default ``Accept`` is ``*/*``. The ``HX-Request`` header is what identifies
that in-page request, so the authoring routes render a page instead of swapping
a JSON payload into the page the author is working in.
"""

from __future__ import annotations

from fastapi import Request


def wants_html(request: Request) -> bool:
    """Return whether the caller expects an HTML page rather than JSON.

    An explicit ``application/json`` request always wins, so API clients keep
    their machine-readable responses. Otherwise a browser navigation or an
    htmx-boosted request expects HTML.
    """
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return False
    if "application/json" in request.headers.get("content-type", ""):
        return False
    return "text/html" in accept or request.headers.get("HX-Request") == "true"
