from __future__ import annotations
from unittest.mock import MagicMock, call, patch

from backend.app.services.genre import GenreService


def _resp(tags: list[dict] | None = None, error: int | None = None) -> MagicMock:
    mock = MagicMock()
    if error is not None:
        mock.json.return_value = {"error": error, "message": "not found"}
    else:
        mock.json.return_value = {"toptags": {"tag": tags or []}}
    return mock


class TestGenreServiceNoKey:
    def test_returns_none_when_key_missing(self, monkeypatch):
        monkeypatch.delenv("LASTFM_API_KEY", raising=False)
        assert GenreService().lookup("Starecase", "Not So Blue") is None

    def test_returns_none_when_key_blank(self, monkeypatch):
        monkeypatch.setenv("LASTFM_API_KEY", "   ")
        assert GenreService().lookup("Starecase", "Not So Blue") is None


class TestGenreServiceTrackTags:
    def test_returns_first_track_tag(self, monkeypatch):
        monkeypatch.setenv("LASTFM_API_KEY", "testkey")
        tags = [{"name": "progressive house", "count": 100}]
        with patch("backend.app.services.genre.requests.get", return_value=_resp(tags)):
            assert GenreService().lookup("Starecase", "Not So Blue") == "progressive house"

    def test_skips_non_genre_tags(self, monkeypatch):
        monkeypatch.setenv("LASTFM_API_KEY", "testkey")
        tags = [{"name": "seen live", "count": 200}, {"name": "tech house", "count": 80}]
        with patch("backend.app.services.genre.requests.get", return_value=_resp(tags)):
            assert GenreService().lookup("Artist", "Track") == "tech house"

    def test_skips_nationality_tags(self, monkeypatch):
        monkeypatch.setenv("LASTFM_API_KEY", "testkey")
        tags = [{"name": "british", "count": 100}, {"name": "House", "count": 25}]
        with patch("backend.app.services.genre.requests.get", return_value=_resp(tags)):
            assert GenreService().lookup("Artist", "Track") == "House"

    def test_returns_none_on_api_error(self, monkeypatch):
        monkeypatch.setenv("LASTFM_API_KEY", "testkey")
        # track error → artist error → None
        with patch("backend.app.services.genre.requests.get", return_value=_resp(error=6)):
            assert GenreService().lookup("Unknown", "Obscure") is None

    def test_returns_none_on_request_exception(self, monkeypatch):
        monkeypatch.setenv("LASTFM_API_KEY", "testkey")
        with patch("backend.app.services.genre.requests.get", side_effect=Exception("timeout")):
            assert GenreService().lookup("Artist", "Track") is None


class TestGenreServiceArtistTagFallback:
    def test_falls_back_to_artist_tags_when_track_empty(self, monkeypatch):
        monkeypatch.setenv("LASTFM_API_KEY", "testkey")
        no_tags = _resp([])
        artist_tags = _resp([{"name": "electronic", "count": 100}])
        with patch("backend.app.services.genre.requests.get", side_effect=[no_tags, artist_tags]):
            assert GenreService().lookup("Daft Punk", "Get Lucky") == "electronic"

    def test_falls_back_to_primary_artist_when_multi_artist_empty(self, monkeypatch):
        monkeypatch.setenv("LASTFM_API_KEY", "testkey")
        # track empty, full-artist empty, primary artist has genre
        no_tags = _resp([])
        primary_tags = _resp([{"name": "House", "count": 25}])
        with patch("backend.app.services.genre.requests.get",
                   side_effect=[no_tags, no_tags, primary_tags]):
            assert GenreService().lookup("Joshwa & Lee Foss", "My Humps") == "House"

    def test_no_primary_fallback_for_single_artist(self, monkeypatch):
        monkeypatch.setenv("LASTFM_API_KEY", "testkey")
        with patch("backend.app.services.genre.requests.get", return_value=_resp([])) as mock_get:
            GenreService().lookup("Starecase", "Not So Blue")
        # only 2 calls: track tags + artist tags (no primary fallback)
        assert mock_get.call_count == 2
