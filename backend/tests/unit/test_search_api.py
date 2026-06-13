from __future__ import annotations
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.result import SearchResponse, SourceResult

client = TestClient(app)


def _result(source="youtube"):
    return SourceResult(
        id="abc123def456abcd",
        title="Test Track",
        artist="Test Artist",
        source=source,  # type: ignore[arg-type]
        thumbnail_url=None,
        source_page_url=f"https://{source}.com/track/test",
        duration_seconds=300,
    )


class TestSearchEndpoint:
    def test_empty_query_returns_400(self):
        resp = client.post("/api/search", json={"query": ""})
        assert resp.status_code == 400

    def test_whitespace_only_returns_400(self):
        resp = client.post("/api/search", json={"query": "   "})
        assert resp.status_code == 400

    def test_missing_body_returns_422(self):
        resp = client.post("/api/search", json={})
        assert resp.status_code == 422

    def test_valid_text_query_returns_results(self):
        fake_response = SearchResponse(
            query="test",
            results=[_result("youtube"), _result("soundcloud")],
            source_errors=[],
        )
        with patch("backend.app.api.search.parallel_search", return_value=fake_response):
            resp = client.post("/api/search", json={"query": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 2
        assert data["source_errors"] == []
        assert data["query"] == "test"

    def test_source_errors_passed_through(self):
        fake_response = SearchResponse(
            query="test",
            results=[_result("youtube")],
            source_errors=["SoundCloud unavailable"],
        )
        with patch("backend.app.api.search.parallel_search", return_value=fake_response):
            resp = client.post("/api/search", json={"query": "test"})
        assert resp.status_code == 200
        assert resp.json()["source_errors"] == ["SoundCloud unavailable"]

    def test_url_query_calls_resolve(self):
        fake_response = SearchResponse(
            query="https://www.youtube.com/watch?v=ABC",
            results=[_result("youtube")],
            source_errors=[],
        )
        with patch("backend.app.api.search.resolve_single_url", return_value=fake_response) as mock_resolve, \
             patch("backend.app.api.search.parallel_search") as mock_search:
            resp = client.post("/api/search", json={"query": "https://www.youtube.com/watch?v=ABC"})
        assert resp.status_code == 200
        mock_resolve.assert_called_once()
        mock_search.assert_not_called()

    def test_unsupported_url_returns_422(self):
        from backend.app.sources.base import UnsupportedURLError
        with patch(
            "backend.app.api.search.resolve_single_url",
            side_effect=UnsupportedURLError("no source"),
        ):
            resp = client.post("/api/search", json={"query": "https://example.com/song"})
        assert resp.status_code == 422

    def test_result_shape(self):
        fake_response = SearchResponse(
            query="track",
            results=[_result("bandcamp")],
            source_errors=[],
        )
        with patch("backend.app.api.search.parallel_search", return_value=fake_response):
            resp = client.post("/api/search", json={"query": "track"})
        r = resp.json()["results"][0]
        assert set(r.keys()) == {
            "id", "title", "artist", "source",
            "thumbnail_url", "source_page_url", "duration_seconds",
            "quality_tier",
        }
        assert r["quality_tier"] == "unknown"
