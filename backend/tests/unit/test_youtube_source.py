from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.app.sources.youtube import YouTubeSource
from backend.app.sources.base import SourceUnavailableError, UnsupportedURLError, NotDownloadableError
from backend.app.models.result import SourceResult


@pytest.fixture
def source():
    return YouTubeSource()


def _fake_entry(**overrides):
    base = {
        "title": "Test Track",
        "uploader": "Test Artist",
        "webpage_url": "https://www.youtube.com/watch?v=ABC123",
        "thumbnail": "https://img.example.com/thumb.jpg",
        "duration": 300,
        "ext": "webm",
    }
    base.update(overrides)
    return base


# --- can_handle_url ---

class TestCanHandleUrl:
    def test_youtube_com(self, source):
        assert source.can_handle_url("https://www.youtube.com/watch?v=ABC")

    def test_youtu_be(self, source):
        assert source.can_handle_url("https://youtu.be/ABC")

    def test_soundcloud_rejected(self, source):
        assert not source.can_handle_url("https://soundcloud.com/artist/track")

    def test_bandcamp_rejected(self, source):
        assert not source.can_handle_url("https://artist.bandcamp.com/track/song")

    def test_random_string_rejected(self, source):
        assert not source.can_handle_url("not a url")


# --- search ---

class TestSearch:
    def test_returns_source_results(self, source):
        fake = {"entries": [_fake_entry(), _fake_entry(title="Track 2", uploader="Artist 2")]}
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            MockYDL.return_value.__enter__.return_value.extract_info.return_value = fake
            results = source.search("test query")
        assert len(results) == 2
        assert all(isinstance(r, SourceResult) for r in results)
        assert all(r.source == "youtube" for r in results)

    def test_empty_entries_returns_empty_list(self, source):
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            MockYDL.return_value.__enter__.return_value.extract_info.return_value = {"entries": []}
            results = source.search("nonexistent")
        assert results == []

    def test_download_error_raises_unavailable(self, source):
        import yt_dlp
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            MockYDL.return_value.__enter__.return_value.extract_info.side_effect = (
                yt_dlp.utils.DownloadError("Network error")
            )
            with pytest.raises(SourceUnavailableError):
                source.search("test")

    def test_result_fields_populated(self, source):
        fake = {"entries": [_fake_entry()]}
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            MockYDL.return_value.__enter__.return_value.extract_info.return_value = fake
            results = source.search("test")
        r = results[0]
        assert r.title == "Test Track"
        assert r.artist == "Test Artist"
        assert r.source_page_url == "https://www.youtube.com/watch?v=ABC123"
        assert r.duration_seconds == 300


# --- resolve_url ---

class TestResolveUrl:
    def test_returns_result(self, source):
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            MockYDL.return_value.__enter__.return_value.extract_info.return_value = _fake_entry()
            result = source.resolve_url("https://www.youtube.com/watch?v=ABC123")
        assert isinstance(result, SourceResult)
        assert result.title == "Test Track"
        assert result.source == "youtube"

    def test_unsupported_url_raises(self, source):
        with pytest.raises(UnsupportedURLError):
            source.resolve_url("https://soundcloud.com/track")

    def test_download_error_raises_unavailable(self, source):
        import yt_dlp
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            MockYDL.return_value.__enter__.return_value.extract_info.side_effect = (
                yt_dlp.utils.DownloadError("Video unavailable")
            )
            with pytest.raises(SourceUnavailableError):
                source.resolve_url("https://www.youtube.com/watch?v=GONE")


# --- prepare_download ---

class TestPrepareDownload:
    def test_returns_file_mime_filename(self, source, tmp_path):
        fake_audio = tmp_path / "audio.mp3"
        fake_audio.write_bytes(b"fake")

        with patch("yt_dlp.YoutubeDL") as MockYDL, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)):
            MockYDL.return_value.__enter__.return_value.extract_info.return_value = _fake_entry(ext="mp3")
            file_path, mime, filename = source.prepare_download(
                "https://www.youtube.com/watch?v=ABC123"
            )

        assert file_path == str(fake_audio)
        assert mime == "audio/mpeg"
        assert "Test Track" in filename

    def test_no_output_file_raises(self, source, tmp_path):
        with patch("yt_dlp.YoutubeDL") as MockYDL, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)):
            MockYDL.return_value.__enter__.return_value.extract_info.return_value = _fake_entry()
            with pytest.raises(NotDownloadableError):
                source.prepare_download("https://www.youtube.com/watch?v=ABC123")

    def test_geo_blocked_raises_not_downloadable(self, source, tmp_path):
        import yt_dlp
        with patch("yt_dlp.YoutubeDL") as MockYDL, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)):
            MockYDL.return_value.__enter__.return_value.extract_info.side_effect = (
                yt_dlp.utils.DownloadError("geo restricted content")
            )
            with pytest.raises(NotDownloadableError):
                source.prepare_download("https://www.youtube.com/watch?v=BLOCKED")
