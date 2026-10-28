"""Optional story imagery for the Fashion & Design Pulse (SPEC-043).

Curated stories may carry one illustrative stock image. The selection happens
only inside the curation workflow, never when a learner opens the feed:

- a short visual query is derived from the story's own grounded text and its
  controlled category, so a sensational or over-long headline is never passed
  through unchanged;
- the existing provider-neutral :class:`~fablit.application.image_search.
  ImageSearchProvider` port is reused, and the search stays bounded;
- candidates are filtered by validated metadata, visual suitability, and
  relevance to the story; an uncertain or weak match yields no image at all;
- the selected image keeps its provenance (provider, source page, creator,
  attribution, alt text, stable asset id) so it can be stored and rendered
  without another search.

Imagery is optional: search failure, empty results, or unusable metadata never
block or remove an otherwise valid text story, and every image is labelled as
illustrative so a generic stock photograph is never presented as evidence of a
specific designer, collection, product, or event.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .errors import UnsafeNewsUrlError
from .image_search import ImageCandidate, ImageSearchError, ImageSearchProvider
from .news_sources import normalize_http_url

#: A visual query must stay short enough to describe a subject, not a story.
MAX_VISUAL_QUERY_CHARS = 120

#: Distinctive words kept from the story text when deriving the visual query.
MAX_QUERY_TERMS = 5

#: A card image is only useful when it has enough detail to be cropped.
MIN_IMAGE_SHORT_SIDE = 400
MIN_IMAGE_LONG_SIDE = 640

#: Extreme aspect ratios crop badly in an editorial card.
MIN_ASPECT_RATIO = 0.5
MAX_ASPECT_RATIO = 2.5

#: Alt text shown to assistive technology when the provider supplies none.
MAX_ALT_TEXT_CHARS = 240

#: Provider identity used when the adapter does not name itself.
UNKNOWN_IMAGE_PROVIDER = "image-search"

#: Controlled category value -> the visual subject the story is about.
_CATEGORY_SUBJECTS: dict[str, str] = {
    "fashion": "fashion design",
    "textiles": "textile fabric",
    "sustainability": "sustainable materials",
    "indian-craft": "handloom craft",
    "design": "design studio",
    "visual-culture": "visual culture",
}

#: Words that carry no visual subject, so they never reach an image search.
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "about",
        "after",
        "against",
        "along",
        "among",
        "another",
        "around",
        "because",
        "been",
        "before",
        "being",
        "between",
        "both",
        "came",
        "come",
        "could",
        "does",
        "doing",
        "done",
        "down",
        "during",
        "each",
        "every",
        "from",
        "had",
        "has",
        "have",
        "here",
        "hers",
        "him",
        "his",
        "how",
        "into",
        "its",
        "just",
        "like",
        "made",
        "make",
        "many",
        "more",
        "most",
        "much",
        "must",
        "new",
        "news",
        "now",
        "only",
        "other",
        "our",
        "out",
        "over",
        "own",
        "said",
        "says",
        "she",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "thing",
        "things",
        "this",
        "those",
        "through",
        "told",
        "too",
        "under",
        "until",
        "very",
        "was",
        "way",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "why",
        "will",
        "with",
        "within",
        "without",
        "would",
        "year",
        "years",
    }
)

_WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")


@dataclass(frozen=True)
class StoryImage:
    """One selected illustrative image and its provenance (SPEC-043 §4.1).

    The value keeps display, credit, and provenance fields together so the
    story can store exactly what was selected and the learner page can render
    attribution without another provider call.
    """

    asset_id: str
    image_url: str
    thumbnail_url: str
    alt_text: str
    source_name: str
    source_url: str
    provider: str
    width: int = 0
    height: int = 0
    credit: str = ""
    creator: str = ""
    creator_url: str = ""
    license_type: str = ""
    is_illustrative: bool = True

    def __post_init__(self) -> None:
        """Validate the display and provenance fields before persistence."""
        for name in (
            "asset_id",
            "image_url",
            "thumbnail_url",
            "alt_text",
            "source_name",
            "source_url",
            "provider",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"story image {name} must be non-blank text")
        for name in ("image_url", "thumbnail_url", "source_url"):
            try:
                normalize_http_url(getattr(self, name))
            except UnsafeNewsUrlError as exc:
                raise ValueError(f"story image {name} is unsafe: {exc}") from exc
        if self.creator_url:
            try:
                normalize_http_url(self.creator_url)
            except UnsafeNewsUrlError as exc:
                raise ValueError(f"story image creator_url is unsafe: {exc}") from exc
        for name in ("width", "height"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"story image {name} must be a non-negative integer")
        if not isinstance(self.is_illustrative, bool):
            raise ValueError("story image is_illustrative must be a boolean")

    @property
    def credit_line(self) -> str:
        """The human-readable credit shown beside the image."""
        return self.credit.strip() or self.creator.strip() or self.source_name


def derive_visual_query(
    headline: str,
    summary: str,
    categories: Iterable[str] = (),
) -> str:
    """Derive a short visual subject query from grounded story text.

    The headline contributes the first distinctive words, the summary only
    fills what the headline lacks, and the story's controlled category adds
    the visual subject. Stop words, over-long text, and repeated words are
    dropped, so the query describes what to picture rather than repeating the
    headline.
    """
    terms = _significant_terms(headline, limit=MAX_QUERY_TERMS - 2)
    if len(terms) < 2:
        for term in _significant_terms(summary, limit=MAX_QUERY_TERMS - 2):
            if term not in terms:
                terms.append(term)
            if len(terms) >= MAX_QUERY_TERMS - 1:
                break
    subject = _category_subject(categories)
    if subject:
        for term in subject.split():
            if term not in terms:
                terms.append(term)
    words = terms[:MAX_QUERY_TERMS]
    if not words and subject:
        return subject
    return _bounded_query(" ".join(words), fallback=subject)


def select_story_image(
    candidates: Iterable[ImageCandidate],
    *,
    query: str,
    provider: str = UNKNOWN_IMAGE_PROVIDER,
) -> StoryImage | None:
    """Select the most suitable candidate, or ``None`` when none is safe.

    A candidate must carry valid public URLs, a usable size, a non-extreme
    aspect ratio, and at least one distinctive word shared with the story's
    visual query. Selection is deliberately conservative: a weak or uncertain
    match returns no image, and the story is published as text only.
    """
    terms = set(_significant_terms(query, limit=MAX_QUERY_TERMS))
    if not terms:
        return None
    best: StoryImage | None = None
    best_key: tuple[int, int, str] | None = None
    for candidate in candidates:
        image = _story_image_from_candidate(candidate, query=query, provider=provider)
        if image is None or not _is_visually_suitable(image):
            continue
        description = f"{candidate.description} {candidate.alt_text}"
        matched = len(terms & set(_significant_terms(description, limit=40)))
        if matched < 1:
            continue
        key = (matched, min(image.width, image.height), image.asset_id)
        if best_key is None or key > best_key:
            best_key, best = key, image
    return best


@dataclass(frozen=True)
class StoryImageSelection:
    """The outcome of one image search during curation (SPEC-043 §4.1).

    ``reason`` is a stable, safe diagnostic for the operator: it never carries
    provider payloads, URLs, or credentials.
    """

    image: StoryImage | None
    reason: str
    query: str = ""
    candidates_considered: int = 0


class NewsImageSelector:
    """Bounded, conservative image selection for one curated story.

    The selector owns query derivation and candidate filtering; the provider
    adapter behind :class:`ImageSearchProvider` stays the only place that
    knows a concrete image service. A failure is reported as a reason, never
    raised, so imagery can never fail publication.
    """

    def __init__(
        self,
        provider: ImageSearchProvider,
        *,
        limit: int = 4,
        provider_id: str = "",
    ) -> None:
        if not callable(getattr(provider, "search", None)):
            raise ValueError("news image selection requires an image-search provider")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("news image selection limit must be positive")
        self._provider = provider
        self._limit = limit
        self._provider_id = provider_id.strip() or _provider_identity(provider)

    @property
    def provider_id(self) -> str:
        """The identity recorded on every selected image."""
        return self._provider_id

    def select(
        self,
        *,
        headline: str,
        summary: str,
        categories: Iterable[str] = (),
    ) -> StoryImageSelection:
        """Search for and select one illustrative image for a story."""
        query = derive_visual_query(headline, summary, categories)
        try:
            candidates = tuple(self._provider.search(query, limit=self._limit))
        except ImageSearchError:
            return StoryImageSelection(
                image=None, reason="image search failed", query=query
            )
        except Exception:
            return StoryImageSelection(
                image=None, reason="image search failed", query=query
            )
        if not candidates:
            return StoryImageSelection(
                image=None, reason="image search returned no results", query=query
            )
        image = select_story_image(candidates, query=query, provider=self._provider_id)
        if image is None:
            return StoryImageSelection(
                image=None,
                reason="no returned image was suitable",
                query=query,
                candidates_considered=len(candidates),
            )
        return StoryImageSelection(
            image=image,
            reason="selected",
            query=query,
            candidates_considered=len(candidates),
        )


def story_image_to_mapping(image: StoryImage) -> dict[str, object]:
    """Serialize a selected image for story persistence."""
    return {
        "asset_id": image.asset_id,
        "image_url": image.image_url,
        "thumbnail_url": image.thumbnail_url,
        "alt_text": image.alt_text,
        "source_name": image.source_name,
        "source_url": image.source_url,
        "provider": image.provider,
        "width": image.width,
        "height": image.height,
        "credit": image.credit,
        "creator": image.creator,
        "creator_url": image.creator_url,
        "license_type": image.license_type,
        "is_illustrative": image.is_illustrative,
    }


def story_image_from_mapping(data: object) -> StoryImage | None:
    """Read one stored image, or ``None`` when it is unusable.

    Story image data is persisted as a plain mapping, so the boundary stays
    defensive: a missing, malformed, or unsafe selection means "no image",
    never a failed feed.
    """
    if not isinstance(data, Mapping):
        return None
    try:
        return StoryImage(
            asset_id=_text(data.get("asset_id")),
            image_url=_text(data.get("image_url")),
            thumbnail_url=_text(data.get("thumbnail_url")),
            alt_text=_text(data.get("alt_text")),
            source_name=_text(data.get("source_name")),
            source_url=_text(data.get("source_url")),
            provider=_text(data.get("provider")) or UNKNOWN_IMAGE_PROVIDER,
            width=_non_negative_int(data.get("width")),
            height=_non_negative_int(data.get("height")),
            credit=_text(data.get("credit")),
            creator=_text(data.get("creator")),
            creator_url=_text(data.get("creator_url")),
            license_type=_text(data.get("license_type")),
            is_illustrative=bool(data.get("is_illustrative", True)),
        )
    except ValueError:
        return None


def _story_image_from_candidate(
    candidate: ImageCandidate,
    *,
    query: str,
    provider: str,
) -> StoryImage | None:
    """Map one provider candidate, rejecting unsafe or incomplete metadata."""
    if not isinstance(candidate, ImageCandidate):
        return None
    try:
        image_url = normalize_http_url(candidate.image_url)
        thumbnail_source = candidate.thumbnail_url.strip() or candidate.image_url
        thumbnail_url = normalize_http_url(thumbnail_source)
        source_url = normalize_http_url(candidate.source_url)
    except UnsafeNewsUrlError:
        return None
    alt_text = _illustrative_alt_text(candidate, query=query)
    if not alt_text:
        return None
    creator_url = ""
    if candidate.photographer_url.strip():
        try:
            creator_url = normalize_http_url(candidate.photographer_url)
        except UnsafeNewsUrlError:
            creator_url = ""
    try:
        return StoryImage(
            asset_id=candidate.photo_id.strip() or source_url,
            image_url=image_url,
            thumbnail_url=thumbnail_url,
            alt_text=alt_text,
            source_name=candidate.source.strip() or _source_name(source_url),
            source_url=source_url,
            provider=provider.strip() or UNKNOWN_IMAGE_PROVIDER,
            width=candidate.width,
            height=candidate.height,
            credit=_clean(candidate.attribution or candidate.photographer),
            creator=_clean(candidate.photographer),
            creator_url=creator_url,
            license_type=_clean(candidate.license_type),
        )
    except ValueError:
        return None


def _illustrative_alt_text(candidate: ImageCandidate, *, query: str) -> str:
    """Describe the image honestly, marking it as illustrative."""
    described = _clean(candidate.alt_text) or _clean(candidate.description)
    if not described:
        described = _clean(query)
    if not described:
        return ""
    return _bounded(f"Illustrative stock image: {described}", MAX_ALT_TEXT_CHARS)


def _is_visually_suitable(image: StoryImage) -> bool:
    """Reject images too small or too oddly shaped for an editorial card."""
    if image.width < 1 or image.height < 1:
        return False
    short_side = min(image.width, image.height)
    long_side = max(image.width, image.height)
    if short_side < MIN_IMAGE_SHORT_SIDE or long_side < MIN_IMAGE_LONG_SIDE:
        return False
    ratio = image.width / image.height
    return MIN_ASPECT_RATIO <= ratio <= MAX_ASPECT_RATIO


def _significant_terms(text: str, *, limit: int) -> list[str]:
    """Return distinctive, de-duplicated words in their original order."""
    terms: list[str] = []
    for word in _WORD.findall(str(text)):
        term = word.casefold().strip("'-")
        if len(term) < 4 or term in _STOP_WORDS or term in terms:
            continue
        terms.append(term)
        if len(terms) >= limit:
            break
    return terms


def _category_subject(categories: Iterable[str]) -> str:
    """Return the visual subject of the story's first controlled category."""
    for category in categories:
        subject = _CATEGORY_SUBJECTS.get(str(category).strip().casefold())
        if subject:
            return subject
    return ""


def _bounded_query(value: str, *, fallback: str) -> str:
    """Trim a query to a whole word within the visual-query limit."""
    query = _clean(value)
    if len(query) <= MAX_VISUAL_QUERY_CHARS:
        return query or _clean(fallback)
    trimmed = query[:MAX_VISUAL_QUERY_CHARS]
    cut = trimmed.rfind(" ")
    if cut > 0:
        trimmed = trimmed[:cut]
    return trimmed.strip() or _clean(fallback)


def _bounded(value: str, limit: int) -> str:
    """Trim text to a whole word within ``limit`` characters."""
    text = _clean(value)
    if len(text) <= limit:
        return text
    trimmed = text[:limit]
    cut = trimmed.rfind(" ")
    if cut > 0:
        trimmed = trimmed[:cut]
    return trimmed.strip()


def _source_name(source_url: str) -> str:
    """Derive a safe display name from an image source page host."""
    host = source_url.split("//", 1)[-1].split("/", 1)[0]
    return host[4:] if host.startswith("www.") else host


def _provider_identity(provider: object) -> str:
    """Read the provider's own identity, falling back to a stable label."""
    value = getattr(provider, "provider_id", "")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return UNKNOWN_IMAGE_PROVIDER


def _clean(value: object) -> str:
    return " ".join(str(value).split()) if isinstance(value, str) else ""


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value
