from __future__ import annotations
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


class TestGenreEndpointBasic:
    def test_missing_artist_returns_422(self):
        resp = client.post("/api/genre", json={"title": "Not So Blue"})
        assert resp.status_code == 422

    def test_missing_title_returns_422(self):
        resp = client.post("/api/genre", json={"artist": "Starecase"})
        assert resp.status_code == 422

    def test_get_method_not_allowed(self):
        resp = client.get("/api/genre")
        assert resp.status_code in (404, 405)


class TestGenreEndpointResults:
    def test_returns_genre_when_service_finds_one(self):
        with patch("backend.app.api.genre.GenreService.lookup", return_value="progressive house"):
            resp = client.post("/api/genre", json={"artist": "Starecase", "title": "Not So Blue"})
        assert resp.status_code == 200
        assert resp.json() == {"genre": "progressive house"}

    def test_returns_null_when_service_returns_none(self):
        with patch("backend.app.api.genre.GenreService.lookup", return_value=None):
            resp = client.post("/api/genre", json={"artist": "Unknown", "title": "Track"})
        assert resp.status_code == 200
        assert resp.json() == {"genre": None}
