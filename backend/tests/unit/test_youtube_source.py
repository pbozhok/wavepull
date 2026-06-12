from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.app.sources.youtube import YouTubeSource, _ydl_probe_quality
from backend.app.sources.base import SourceUnavailableError, UnsupportedURLError, NotDownloadableError
from backend.app.models.result import QualityTier, SourceResult


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

    def test_format_selector_prefers_flac(self, source, tmp_path):
        fake_audio = tmp_path / "audio.flac"
        fake_audio.write_bytes(b"fake")
        captured_opts = {}

        def capture_ydl(opts):
            captured_opts.update(opts)
            m = MagicMock()
            m.__enter__ = lambda s: m
            m.__exit__ = MagicMock(return_value=False)
            m.extract_info.return_value = _fake_entry(ext="flac")
            return m

        with patch("yt_dlp.YoutubeDL", side_effect=capture_ydl), \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)):
            source.prepare_download("https://www.youtube.com/watch?v=ABC123")

        fmt = captured_opts.get("format", "")
        assert "bestaudio[ext=flac]" in fmt
        assert "bestaudio[abr>=320]" in fmt
        assert "postprocessors" not in captured_opts


# --- probe_quality ---

class TestProbeQuality:
    def _make_ydl_mock(self, formats):
        m = MagicMock()
        m.__enter__ = lambda s: m
        m.__exit__ = MagicMock(return_value=False)
        m.extract_info.return_value = {"formats": formats}
        return m

    def test_flac_format_returns_flac(self, source):
        fmts = [{"ext": "flac", "acodec": "flac", "abr": None}]
        with patch("yt_dlp.YoutubeDL", return_value=self._make_ydl_mock(fmts)):
            assert source.probe_quality("https://www.youtube.com/watch?v=X") == QualityTier.FLAC

    def test_320kbps_mp3_returns_hi_mp3(self, source):
        fmts = [{"ext": "mp3", "acodec": "mp3", "abr": 320}]
        with patch("yt_dlp.YoutubeDL", return_value=self._make_ydl_mock(fmts)):
            assert source.probe_quality("https://www.youtube.com/watch?v=X") == QualityTier.HI_MP3

    def test_low_bitrate_returns_standard(self, source):
        fmts = [{"ext": "mp3", "acodec": "mp3", "abr": 128}]
        with patch("yt_dlp.YoutubeDL", return_value=self._make_ydl_mock(fmts)):
            assert source.probe_quality("https://www.youtube.com/watch?v=X") == QualityTier.STANDARD

    def test_exception_returns_unknown(self, source):
        import yt_dlp
        m = MagicMock()
        m.__enter__ = lambda s: m
        m.__exit__ = MagicMock(return_value=False)
        m.extract_info.side_effect = yt_dlp.utils.DownloadError("blocked")
        with patch("yt_dlp.YoutubeDL", return_value=m):
            assert source.probe_quality("https://www.youtube.com/watch?v=X") == QualityTier.UNKNOWN

    def test_flac_beats_320_when_both_present(self, source):
        fmts = [
            {"ext": "mp3", "acodec": "mp3", "abr": 320},
            {"ext": "flac", "acodec": "flac", "abr": None},
        ]
        with patch("yt_dlp.YoutubeDL", return_value=self._make_ydl_mock(fmts)):
            assert source.probe_quality("https://www.youtube.com/watch?v=X") == QualityTier.FLAC
