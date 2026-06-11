from __future__ import annotations
from unittest.mock import MagicMock, patch

import pytest

from backend.app.sources.bandcamp import BandcampSource
from backend.app.sources.base import SourceUnavailableError, UnsupportedURLError
from backend.app.models.result import SourceResult

_SEARCH_HTML = """
<ul>
  <li class="searchresult track">
    <div class="art"><img src="https://img.bc.com/art.jpg"></div>
    <div class="heading"><a href="https://artist.bandcamp.com/track/my-track">My Track</a></div>
    <div class="subhead">by The Artist</div>
  </li>
  <li class="searchresult track">
    <div class="art"><img src="https://img.bc.com/art2.jpg"></div>
    <div class="heading"><a href="https://other.bandcamp.com/track/other-track">Other Track</a></div>
    <div class="subhead">by Other Artist</div>
  </li>
</ul>
"""


@pytest.fixture
def source():
    return BandcampSource()


class TestCanHandleUrl:
    def test_subdomain_bandcamp(self, source):
        assert source.can_handle_url("https://artist.bandcamp.com/track/song")

    def test_youtube_rejected(self, source):
        assert not source.can_handle_url("https://www.youtube.com/watch?v=ABC")

    def test_soundcloud_rejected(self, source):
        assert not source.can_handle_url("https://soundcloud.com/artist/track")

    def test_bare_bandcamp_com_rejected(self, source):
        assert not source.can_handle_url("https://bandcamp.com/search")


class TestSearch:
    def test_text_search_returns_empty(self, source):
        # Bandcamp blocks server-side requests; text search is intentionally disabled.
        results = source.search("aphex twin")
        assert results == []

    def test_text_search_any_limit_returns_empty(self, source):
        assert source.search("test", limit=1) == []


class TestResolveUrl:
    def test_returns_result(self, source):
        fake_info = {
            "title": "BC Track",
            "uploader": "BC Artist",
            "webpage_url": "https://artist.bandcamp.com/track/bc-track",
            "thumbnail": None,
            "duration": 200,
        }
        with patch("yt_dlp.YoutubeDL") as MockYDL:
            MockYDL.return_value.__enter__.return_value.extract_info.return_value = fake_info
            result = source.resolve_url("https://artist.bandcamp.com/track/bc-track")
        assert isinstance(result, SourceResult)
        assert result.source == "bandcamp"
        assert result.title == "BC Track"

    def test_unsupported_url_raises(self, source):
        with pytest.raises(UnsupportedURLError):
            source.resolve_url("https://www.youtube.com/watch?v=ABC")


class TestPrepareDownload:
    def test_returns_file_mime_filename(self, source, tmp_path):
        fake_audio = tmp_path / "audio.mp3"
        fake_audio.write_bytes(b"fake")

        fake_info = {
            "title": "BC Track",
            "uploader": "BC Artist",
            "ext": "mp3",
        }
        with patch("yt_dlp.YoutubeDL") as MockYDL, \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)):
            MockYDL.return_value.__enter__.return_value.extract_info.return_value = fake_info
            file_path, mime, filename = source.prepare_download(
                "https://artist.bandcamp.com/track/bc-track"
            )

        assert mime == "audio/mpeg"
        assert "BC Track" in filename
