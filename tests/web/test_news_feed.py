"""Web tests for the SPEC-041 learner feed and protected curation action."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from fablit.application.news import (
    InMemoryNewsRepository,
    NewsCategory,
    NewsCurator,
    NewsStory,
)
from fablit.application.news_curation import FakeNewsCurationProvider
from fablit.application.news_sources import (
    FakeNewsSourceFetcher,
    NewsSource,
    NewsSourceItem,
)
from fablit.application.persistence import PersistenceError

SECRET = "news-authoring-secret"
HEADERS = {"Authorization": f"Bearer {SECRET}"}
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
SOURCE = NewsSource(
    name="The Daily Weave",
    feed_url="https://news.example.com/feed.xml",
    site_url="https://news.example.com",
)
SOURCES = [
    {
        "name": SOURCE.name,
        "feed_url": SOURCE.feed_url,
        "site_url": SOURCE.site_url,
    }
]


def _app() -> FastAPI:
    from fablit.config import load_config

    return create_app(
        load_config(
            overrides={
                "environment": "testing",
                "authoring_secret": SECRET,
                "news_repository": "memory",
                "news_sources": SOURCES,
            }
        )
    )


def _client() -> tuple[TestClient, FastAPI]:
    app = _app()
    return TestClient(app), app


def make_story(**overrides: object) -> NewsStory:
    story_id = uuid4()
    values: dict[str, object] = {
        "story_id": story_id,
        "headline": "Handloom revival connects weavers with new markets",
        "canonical_url": f"https://news.example.com/story/{story_id}",
        "source_name": SOURCE.name,
        "summary": (
            "A new collective is helping handloom weavers bring traditional "
            "textiles to contemporary fashion buyers."
        ),
        "categories": (NewsCategory.FASHION, NewsCategory.INDIAN_CRAFT),
        "educational_relevance": (
            "Notice how material knowledge and local craft meet contemporary design."
        ),
        "retrieved_at": NOW,
        "curated_at": NOW,
        "published_at": NOW - timedelta(days=1),
        "reflection_prompt": "Where do you see a material tradition nearby?",
        "provider": "fake-news-curation",
        "model": "fake-model",
    }
    values.update(overrides)
    return NewsStory(**values)  # type: ignore[arg-type]


def make_item(**overrides: object) -> NewsSourceItem:
    values: dict[str, object] = {
        "source_name": SOURCE.name,
        "title": "Handloom revival connects weavers with new markets",
        "url": "https://news.example.com/story/1",
        "published_at": NOW - timedelta(days=1),
        "excerpt": "A collective is helping handloom weavers reach new buyers.",
    }
    values.update(overrides)
    return NewsSourceItem(**values)  # type: ignore[arg-type]


def install_curator(
    app: FastAPI,
    *,
    items: tuple[NewsSourceItem, ...] = (),
    provider: FakeNewsCurationProvider | None = None,
) -> NewsCurator:
    repository = app.state.news_repository
    assert isinstance(repository, InMemoryNewsRepository)
    curator = NewsCurator(
        repository=repository,
        fetcher=FakeNewsSourceFetcher(default=items),
        provider=provider or FakeNewsCurationProvider(),
        sources=(SOURCE,),
        clock=lambda: NOW,
    )
    app.state.news_curator = curator
    return curator


# --- Learner feed ------------------------------------------------------------


def test_feed_renders_persisted_stories_with_attribution_and_categories() -> None:
    client, app = _client()
    story = make_story()
    app.state.news_repository.save(story)

    response = client.get("/pulse")

    assert response.status_code == 200
    assert story.headline in response.text
    assert story.summary in response.text
    assert story.source_name in response.text
    assert "Fashion" in response.text
    assert "Indian craft" in response.text
    assert story.educational_relevance in response.text
    assert story.reflection_prompt is not None
    assert story.reflection_prompt in response.text
    assert f'href="{story.canonical_url}"' in response.text
    assert 'rel="noopener noreferrer nofollow"' in response.text
    assert "19 October 2026" in response.text


def test_feed_orders_newest_stories_first() -> None:
    client, app = _client()
    older = make_story(headline="Older story", published_at=NOW - timedelta(days=5))
    newer = make_story(headline="Newer story", published_at=NOW - timedelta(days=1))
    app.state.news_repository.save(older)
    app.state.news_repository.save(newer)

    response = client.get("/pulse")

    assert response.text.index("Newer story") < response.text.index("Older story")


def test_feed_filters_by_category() -> None:
    client, app = _client()
    fashion = make_story(headline="A fashion story", categories=(NewsCategory.FASHION,))
    craft = make_story(
        headline="A craft story", categories=(NewsCategory.INDIAN_CRAFT,)
    )
    app.state.news_repository.save(fashion)
    app.state.news_repository.save(craft)

    response = client.get("/pulse?category=fashion")

    assert response.status_code == 200
    assert "A fashion story" in response.text
    assert "A craft story" not in response.text
    assert 'aria-current="true"' in response.text


def test_feed_ignores_an_unknown_category_filter() -> None:
    client, app = _client()
    app.state.news_repository.save(make_story(headline="A fashion story"))

    response = client.get("/pulse?category=astronomy")

    assert response.status_code == 200
    assert "A fashion story" in response.text


def test_feed_escapes_source_text_and_never_links_an_unsafe_url() -> None:
    client, app = _client()
    story = make_story(headline="<script>alert('x')</script>")
    object.__setattr__(story, "canonical_url", "javascript:alert(1)")
    app.state.news_repository.save(story)

    response = client.get("/pulse")

    assert response.status_code == 200
    assert "<script>alert('x')</script>" not in response.text
    assert "&lt;script&gt;" in response.text
    assert 'href="javascript:' not in response.text


def test_feed_shows_a_useful_empty_state() -> None:
    client, _ = _client()

    response = client.get("/pulse")

    assert response.status_code == 200
    assert "No stories yet" in response.text
    assert "plenty to explore in practice" in response.text


class _UnavailableRepository(InMemoryNewsRepository):
    def list_stories(self) -> tuple[NewsStory, ...]:
        raise PersistenceError("simulated store outage")


def test_feed_degrades_gracefully_when_the_store_is_unavailable() -> None:
    client, app = _client()
    app.state.news_repository = _UnavailableRepository()

    response = client.get("/pulse")

    assert response.status_code == 200
    assert "The Pulse is temporarily unavailable" in response.text
    assert client.get("/").status_code == 200
    assert client.get("/history").status_code == 200


def test_feed_works_without_ai_configuration_or_any_curation_call() -> None:
    client, app = _client()
    app.state.news_repository.save(make_story())
    fetcher = Mock()
    provider = Mock()
    app.state.news_curator = Mock(fetch=fetcher, provider=provider)

    response = client.get("/pulse")

    assert response.status_code == 200
    fetcher.fetch.assert_not_called()
    provider.curate.assert_not_called()


def test_primary_navigation_exposes_practice_and_stories() -> None:
    client, _ = _client()

    response = client.get("/")

    assert response.status_code == 200
    assert 'href="/practice"' in response.text
    assert 'href="/pulse"' in response.text
    assert '>Practice</a>' in response.text
    assert '>Stories</a>' in response.text
    assert 'href="/practice"\n         aria-current="page"' in response.text


def test_primary_navigation_marks_stories_as_current_on_pulse() -> None:
    client, _ = _client()

    response = client.get("/pulse")

    assert response.status_code == 200
    assert 'href="/pulse"\n         aria-current="page"' in response.text
    assert 'href="/practice"\n         aria-current="page"' not in response.text


# --- Protected authoring action ---------------------------------------------


def test_unauthorized_curation_is_rejected_before_any_fetch_or_ai_call() -> None:
    client, app = _client()
    fetcher = Mock()
    provider = Mock()
    provider.provider_id = "spy"
    provider.model_id = "spy"
    app.state.news_curator = NewsCurator(
        repository=app.state.news_repository,
        fetcher=fetcher,
        provider=provider,
        sources=(SOURCE,),
    )

    response = client.post("/authoring/pulse/curate")

    assert response.status_code == 401
    fetcher.fetch.assert_not_called()
    provider.curate.assert_not_called()


def test_unauthorized_curation_page_is_rejected() -> None:
    client, _ = _client()

    response = client.get("/authoring/pulse")

    assert response.status_code == 401


def test_authorized_curation_publishes_and_reports_counts() -> None:
    client, app = _client()
    install_curator(app, items=(make_item(),))

    response = client.post("/authoring/pulse/curate", headers=HEADERS)

    assert response.status_code == 200
    assert "1 fetched, 0 duplicates, 1 published, 0 rejected, 0 failed" in response.text
    assert "Handloom revival" not in response.text  # no article body, only the report
    assert client.get("/pulse").text.count('<h2 class="card__title">') == 1


def test_repeated_curation_is_idempotent() -> None:
    client, app = _client()
    install_curator(app, items=(make_item(),))

    first = client.post("/authoring/pulse/curate", headers=HEADERS)
    second = client.post("/authoring/pulse/curate", headers=HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert "1 fetched, 1 duplicate, 0 published, 0 rejected, 0 failed" in second.text
    assert len(app.state.news_repository.list_stories()) == 1


def test_curation_without_a_provider_reports_configuration_not_success() -> None:
    client, app = _client()
    assert app.state.news_curator is None

    response = client.post("/authoring/pulse/curate", headers=HEADERS)

    assert response.status_code == 503
    assert "not configured" in response.text
    assert app.state.news_repository.list_stories() == ()


def test_overlapping_curation_is_refused() -> None:
    client, app = _client()
    curator = install_curator(app, items=(make_item(),))

    assert curator._lock.acquire(blocking=False)
    try:
        response = client.post("/authoring/pulse/curate", headers=HEADERS)
    finally:
        curator._lock.release()

    assert response.status_code == 409
    assert "already running" in response.text


def test_batch_report_shows_rejections_without_raw_provider_detail() -> None:
    client, app = _client()
    provider = FakeNewsCurationProvider(error=RuntimeError("secret upstream payload"))
    install_curator(app, items=(make_item(),), provider=provider)

    client.post("/authoring/pulse/curate", headers=HEADERS)

    page = client.get("/authoring/pulse", headers=HEADERS)
    assert page.status_code == 200
    assert "1 fetched, 0 duplicates, 0 published, 0 rejected, 1 failed" in page.text
    assert "curation provider failed" in page.text
    assert "secret upstream payload" not in page.text


def test_authoring_workspace_offers_the_curation_action() -> None:
    client, _ = _client()

    page = client.get("/authoring", headers=HEADERS)

    assert page.status_code == 200
    assert 'action="/authoring/pulse/curate"' in page.text
    assert "Curate this week's news" in page.text
    assert 'href="/authoring/pulse"' in page.text


def test_authoring_page_lists_sources_and_configuration_warnings() -> None:
    client, app = _client()
    page = client.get("/authoring/pulse", headers=HEADERS)

    assert page.status_code == 200
    assert SOURCE.name in page.text
    assert "AI curation is not configured" in page.text
    assert "Curate this week's news" in page.text
