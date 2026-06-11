from __future__ import annotations
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.sources.base import NotDownloadableError, SourceUnavailableError

client = TestClient(app)

_YT_URL = "https://www.youtube.com/watch?v=ABC123"
_ENCODED = "https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DABC123"


class TestDownloadEndpoint:
    def test_missing_url_returns_422(self):
        resp = client.get("/api/download")
        assert resp.status_code == 422

    def test_unsupported_url_returns_422(self):
        with patch("backend.app.api.download.find_source_for_url", return_value=None):
            resp = client.get(f"/api/download?url={_ENCODED}")
        assert resp.status_code == 422

    def test_successful_download_returns_file(self, tmp_path):
        fake_audio = tmp_path / "track.mp3"
        fake_audio.write_bytes(b"fake audio data")

        mock_source = MagicMock()
        mock_source.prepare_download.return_value = (
            str(fake_audio), "audio/mpeg", "Artist - Track.mp3"
        )

        with patch("backend.app.api.download.find_source_for_url", return_value=mock_source):
            resp = client.get(f"/api/download?url={_ENCODED}")

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("audio/mpeg")
        assert "attachment" in resp.headers.get("content-disposition", "")

    def test_not_downloadable_returns_422(self):
        mock_source = MagicMock()
        mock_source.prepare_download.side_effect = NotDownloadableError("geo blocked")

        with patch("backend.app.api.download.find_source_for_url", return_value=mock_source):
            resp = client.get(f"/api/download?url={_ENCODED}")

        assert resp.status_code == 422
        assert "cannot be downloaded" in resp.json()["detail"]

    def test_source_unavailable_returns_503(self):
        mock_source = MagicMock()
        mock_source.prepare_download.side_effect = SourceUnavailableError("timeout")

        with patch("backend.app.api.download.find_source_for_url", return_value=mock_source):
            resp = client.get(f"/api/download?url={_ENCODED}")

        assert resp.status_code == 503
