from __future__ import annotations
from unittest.mock import patch

import pytest

from backend.app.sources.soundcloud import SoundCloudSource
from backend.app.sources.base import SourceUnavailableError, UnsupportedURLError
from backend.app.models.result import SourceResult


@pytest.fixture
def source():
    return SoundCloudSource()


def _fake_entry(**overrides):
    base = {
        "title": "SC Track",
        "uploader": "SC Artist",
        "webpage_url": "https://soundcloud.com/scartist/sctrack",
        "thumbnail": "https://img.example.com/sc_thumb.jpg",
        "duration": 240,
        "ext": "mp3",
    }
    base.update(overrides)
    return base


class TestCanHandleUrl:
    def test_soundcloud_com(self, source):
        assert source.can_handle_url("https://soundcloud.com/artist/track")

    def test_www_soundcloud_com(self, source):
        assert source.can_handle_url("https://www.soundcloud.com/artist/track")

    def test_youtube_rejected(self, source):
        assert not source.can_handle_url("https://www.youtube.com/watch?v=ABC")

    def test_bandcamp_rejected(self, source):
        assert not source.can_handle_url("https://artist.bandcamp.com/track/song")


class TestSearch:
    def test_returns_source_results(self, source):
        fake = {"entries": [_fake_entry(), _fake_entry(title="Track 2")]}
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            MockYDL.return_value.__enter__.return_value.extract_info.return_value = fake
            results = source.search("techno")
        assert len(results) == 2
        assert all(r.source == "soundcloud" for r in results)

    def test_uses_scsearch_prefix(self, source):
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            inst = MockYDL.return_value.__enter__.return_value
            inst.extract_info.return_value = {"entries": []}
            source.search("test", limit=3)
            call_args = inst.extract_info.call_args[0][0]
        assert call_args.startswith("scsearch3:")

    def test_download_error_raises_unavailable(self, source):
        import yt_dlp
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            MockYDL.return_value.__enter__.return_value.extract_info.side_effect = (
                yt_dlp.utils.DownloadError("rate limited")
            )
            with pytest.raises(SourceUnavailableError):
                source.search("test")


class TestResolveUrl:
    def test_returns_result(self, source):
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            MockYDL.return_value.__enter__.return_value.extract_info.return_value = _fake_entry()
            result = source.resolve_url("https://soundcloud.com/scartist/sctrack")
        assert isinstance(result, SourceResult)
        assert result.source == "soundcloud"

    def test_unsupported_url_raises(self, source):
        with pytest.raises(UnsupportedURLError):
            source.resolve_url("https://www.youtube.com/watch?v=ABC")


class TestPrepareDownload:
    def test_returns_file_mime_filename(self, source, tmp_path):
        fake_audio = tmp_path / "audio.mp3"
        fake_audio.write_bytes(b"fake")

        with patch("yt_dlp.YoutubeDL") as MockYDL, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)):
            MockYDL.return_value.__enter__.return_value.extract_info.return_value = _fake_entry(ext="mp3")
            file_path, mime, filename = source.prepare_download(
                "https://soundcloud.com/scartist/sctrack"
            )

        assert mime == "audio/mpeg"
        assert "SC Track" in filename
