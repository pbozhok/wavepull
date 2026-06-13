from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.result import DownloadMetadata
from backend.app.sources.base import NotDownloadableError, SourceUnavailableError

client = TestClient(app)

_YT_URL = "https://www.youtube.com/watch?v=ABC123"

_FULL_BODY = {
    "url": _YT_URL,
    "title": "Xtal",
    "artist": "Aphex Twin",
    "album": "Selected Ambient Works",
    "year": "1992",
    "genre": "ambient",
    "thumbnail_url": "https://i.ytimg.com/vi/ABC123/hqdefault.jpg",
}


def _mock_source(tmp_path: Path) -> MagicMock:
    fake_audio = tmp_path / "track.mp3"
    fake_audio.write_bytes(b"fake audio data")
    src = MagicMock()
    src.prepare_download.return_value = (str(fake_audio), "audio/mpeg", "Aphex Twin - Xtal.mp3")
    return src


class TestDownloadEndpointBasic:
    def test_missing_url_field_returns_422(self):
        resp = client.post("/api/download", json={"title": "T", "artist": "A"})
        assert resp.status_code == 422

    def test_missing_title_returns_422(self):
        resp = client.post("/api/download", json={"url": _YT_URL, "artist": "A"})
        assert resp.status_code == 422

    def test_missing_artist_returns_422(self):
        resp = client.post("/api/download", json={"url": _YT_URL, "title": "T"})
        assert resp.status_code == 422

    def test_blank_title_returns_422(self):
        body = {**_FULL_BODY, "title": "   "}
        resp = client.post("/api/download", json=body)
        assert resp.status_code == 422

    def test_blank_artist_returns_422(self):
        body = {**_FULL_BODY, "artist": ""}
        resp = client.post("/api/download", json=body)
        assert resp.status_code == 422

    def test_invalid_year_returns_422(self):
        body = {**_FULL_BODY, "year": "99"}
        resp = client.post("/api/download", json=body)
        assert resp.status_code == 422

    def test_non_numeric_year_returns_422(self):
        body = {**_FULL_BODY, "year": "abcd"}
        resp = client.post("/api/download", json=body)
        assert resp.status_code == 422

    def test_unsupported_url_returns_422(self):
        with patch("backend.app.api.download.find_source_for_url", return_value=None):
            resp = client.post("/api/download", json=_FULL_BODY)
        assert resp.status_code == 422

    def test_get_method_not_allowed(self):
        resp = client.get(f"/api/download?url={_YT_URL}")
        assert resp.status_code in (404, 405)


class TestDownloadEndpointSuccess:
    def test_successful_download_returns_file(self, tmp_path):
        src = _mock_source(tmp_path)
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            resp = client.post("/api/download", json=_FULL_BODY)

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("audio/mpeg")
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_metadata_passed_to_prepare_download(self, tmp_path):
        src = _mock_source(tmp_path)
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            client.post("/api/download", json=_FULL_BODY)

        src.prepare_download.assert_called_once()
        _, metadata = src.prepare_download.call_args.args
        assert isinstance(metadata, DownloadMetadata)
        assert metadata.title == "Xtal"
        assert metadata.artist == "Aphex Twin"
        assert metadata.album == "Selected Ambient Works"
        assert metadata.year == "1992"
        assert metadata.genre == "ambient"
        assert metadata.thumbnail_url == "https://i.ytimg.com/vi/ABC123/hqdefault.jpg"

    def test_genre_passed_when_provided(self, tmp_path):
        src = _mock_source(tmp_path)
        body = {**_FULL_BODY, "genre": "progressive house"}
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            client.post("/api/download", json=body)
        _, metadata = src.prepare_download.call_args.args
        assert metadata.genre == "progressive house"

    def test_genre_empty_when_omitted(self, tmp_path):
        src = _mock_source(tmp_path)
        body = {"url": _YT_URL, "title": "Track", "artist": "Artist"}
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            client.post("/api/download", json=body)
        _, metadata = src.prepare_download.call_args.args
        assert metadata.genre == ""

    def test_genre_trimmed(self, tmp_path):
        src = _mock_source(tmp_path)
        body = {**_FULL_BODY, "genre": "  house  "}
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            client.post("/api/download", json=body)
        _, metadata = src.prepare_download.call_args.args
        assert metadata.genre == "house"

    def test_empty_genre_is_valid(self, tmp_path):
        src = _mock_source(tmp_path)
        body = {**_FULL_BODY, "genre": ""}
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            resp = client.post("/api/download", json=body)
        assert resp.status_code == 200

    def test_whitespace_only_genre_treated_as_empty(self, tmp_path):
        src = _mock_source(tmp_path)
        body = {**_FULL_BODY, "genre": "   "}
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            client.post("/api/download", json=body)
        _, metadata = src.prepare_download.call_args.args
        assert metadata.genre == ""

    def test_empty_year_is_valid(self, tmp_path):
        src = _mock_source(tmp_path)
        body = {**_FULL_BODY, "year": ""}
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            resp = client.post("/api/download", json=body)
        assert resp.status_code == 200

    def test_empty_album_is_valid(self, tmp_path):
        src = _mock_source(tmp_path)
        body = {**_FULL_BODY, "album": ""}
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            resp = client.post("/api/download", json=body)
        assert resp.status_code == 200

    def test_empty_optional_fields_passed_as_empty_strings(self, tmp_path):
        src = _mock_source(tmp_path)
        body = {"url": _YT_URL, "title": "Track", "artist": "Artist"}
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            client.post("/api/download", json=body)

        _, metadata = src.prepare_download.call_args.args
        assert metadata.album == ""
        assert metadata.year == ""

    def test_not_downloadable_returns_422(self, tmp_path):
        src = MagicMock()
        src.prepare_download.side_effect = NotDownloadableError("geo blocked")
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            resp = client.post("/api/download", json=_FULL_BODY)
        assert resp.status_code == 422
        assert "cannot be downloaded" in resp.json()["detail"]

    def test_source_unavailable_returns_503(self, tmp_path):
        src = MagicMock()
        src.prepare_download.side_effect = SourceUnavailableError("timeout")
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            resp = client.post("/api/download", json=_FULL_BODY)
        assert resp.status_code == 503


class TestWriteMetadata:
    def test_write_metadata_sets_tags(self, tmp_path):
        from backend.app.sources.youtube import _write_metadata

        fake_mp3 = tmp_path / "track.mp3"
        fake_mp3.write_bytes(b"\xff\xfb" + b"\x00" * 100)

        metadata = DownloadMetadata(title="Xtal", artist="Aphex Twin", album="SAW", year="1992")

        mock_audio = MagicMock()
        mock_audio.tags = {}

        with patch("backend.app.sources.youtube.MutagenFile", return_value=mock_audio):
            _write_metadata(str(fake_mp3), metadata)

        mock_audio.__setitem__.assert_any_call("title", ["Xtal"])
        mock_audio.__setitem__.assert_any_call("artist", ["Aphex Twin"])
        mock_audio.__setitem__.assert_any_call("album", ["SAW"])
        mock_audio.__setitem__.assert_any_call("date", ["1992"])
        mock_audio.save.assert_called_once()

    def test_write_metadata_skips_empty_fields(self, tmp_path):
        from backend.app.sources.youtube import _write_metadata

        metadata = DownloadMetadata(title="Track", artist="Artist", album="", year="")

        mock_audio = MagicMock()
        mock_audio.tags = {}

        with patch("backend.app.sources.youtube.MutagenFile", return_value=mock_audio):
            _write_metadata("dummy.mp3", metadata)

        set_keys = [c.args[0] for c in mock_audio.__setitem__.call_args_list]
        assert "album" not in set_keys
        assert "date" not in set_keys
        assert "genre" not in set_keys
        mock_audio.save.assert_called_once()

    def test_write_metadata_sets_genre(self, tmp_path):
        from backend.app.sources.youtube import _write_metadata

        metadata = DownloadMetadata(title="Track", artist="Artist", genre="progressive house")
        mock_audio = MagicMock()
        mock_audio.tags = {}
        with patch("backend.app.sources.youtube.MutagenFile", return_value=mock_audio):
            _write_metadata("dummy.mp3", metadata)
        mock_audio.__setitem__.assert_any_call("genre", ["progressive house"])

    def test_write_metadata_skips_empty_genre(self, tmp_path):
        from backend.app.sources.youtube import _write_metadata

        metadata = DownloadMetadata(title="Track", artist="Artist", genre="")
        mock_audio = MagicMock()
        mock_audio.tags = {}
        with patch("backend.app.sources.youtube.MutagenFile", return_value=mock_audio):
            _write_metadata("dummy.mp3", metadata)
        set_keys = [c.args[0] for c in mock_audio.__setitem__.call_args_list]
        assert "genre" not in set_keys

    def test_write_metadata_noop_when_mutagen_returns_none(self):
        from backend.app.sources.youtube import _write_metadata

        metadata = DownloadMetadata(title="T", artist="A")

        with patch("backend.app.sources.youtube.MutagenFile", return_value=None):
            _write_metadata("dummy.mp3", metadata)

    def test_write_metadata_embeds_cover_art_when_thumbnail_url_set(self, tmp_path):
        from backend.app.sources.youtube import _write_metadata

        metadata = DownloadMetadata(
            title="Track", artist="Artist",
            thumbnail_url="https://example.com/cover.jpg",
        )
        mock_audio = MagicMock()
        mock_audio.tags = {}
        fake_image = b"\xff\xd8\xff" + b"\x00" * 50

        with patch("backend.app.sources.youtube.MutagenFile", return_value=mock_audio), \
             patch("backend.app.sources.youtube._fetch_thumbnail", return_value=(fake_image, "image/jpeg")) as mock_fetch, \
             patch("backend.app.sources.youtube._embed_cover_art") as mock_embed:
            _write_metadata("dummy.mp3", metadata)

        mock_fetch.assert_called_once_with("https://example.com/cover.jpg")
        mock_embed.assert_called_once_with("dummy.mp3", fake_image, "image/jpeg")

    def test_write_metadata_skips_cover_art_when_thumbnail_url_empty(self, tmp_path):
        from backend.app.sources.youtube import _write_metadata

        metadata = DownloadMetadata(title="Track", artist="Artist", thumbnail_url="")
        mock_audio = MagicMock()
        mock_audio.tags = {}

        with patch("backend.app.sources.youtube.MutagenFile", return_value=mock_audio), \
             patch("backend.app.sources.youtube._fetch_thumbnail") as mock_fetch, \
             patch("backend.app.sources.youtube._embed_cover_art") as mock_embed:
            _write_metadata("dummy.mp3", metadata)

        mock_fetch.assert_not_called()
        mock_embed.assert_not_called()

    def test_write_metadata_skips_cover_art_when_fetch_fails(self, tmp_path):
        from backend.app.sources.youtube import _write_metadata

        metadata = DownloadMetadata(
            title="Track", artist="Artist",
            thumbnail_url="https://example.com/cover.jpg",
        )
        mock_audio = MagicMock()
        mock_audio.tags = {}

        with patch("backend.app.sources.youtube.MutagenFile", return_value=mock_audio), \
             patch("backend.app.sources.youtube._fetch_thumbnail", return_value=None), \
             patch("backend.app.sources.youtube._embed_cover_art") as mock_embed:
            _write_metadata("dummy.mp3", metadata)

        mock_embed.assert_not_called()

    def test_thumbnail_url_passed_to_metadata(self, tmp_path):
        src = _mock_source(tmp_path)
        body = {**_FULL_BODY, "thumbnail_url": "https://example.com/art.jpg"}
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            client.post("/api/download", json=body)
        _, metadata = src.prepare_download.call_args.args
        assert metadata.thumbnail_url == "https://example.com/art.jpg"

    def test_thumbnail_url_empty_when_omitted(self, tmp_path):
        src = _mock_source(tmp_path)
        body = {"url": _YT_URL, "title": "Track", "artist": "Artist"}
        with patch("backend.app.api.download.find_source_for_url", return_value=src):
            client.post("/api/download", json=body)
        _, metadata = src.prepare_download.call_args.args
        assert metadata.thumbnail_url == ""
