from __future__ import annotations
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.result import QualityTier

client = TestClient(app)

_YT_URL = "https://www.youtube.com/watch?v=ABC123"
_SC_URL = "https://soundcloud.com/artist/track"
_BC_URL = "https://artist.bandcamp.com/track/song"
_UNKNOWN_URL = "https://example.com/not-a-source"


def _mock_source(tier: QualityTier) -> MagicMock:
    src = MagicMock()
    src.probe_quality.return_value = tier
    return src


class TestQualityEndpoint:
    def test_empty_urls_returns_400(self):
        resp = client.post("/api/quality", json={"urls": []})
        assert resp.status_code == 400

    def test_missing_urls_field_returns_422(self):
        resp = client.post("/api/quality", json={})
        assert resp.status_code == 422

    def test_single_flac_url_returns_flac(self):
        mock_src = _mock_source(QualityTier.FLAC)
        with patch("backend.app.api.quality.find_source_for_url", return_value=mock_src):
            resp = client.post("/api/quality", json={"urls": [_BC_URL]})
        assert resp.status_code == 200
        assert resp.json()["results"][_BC_URL] == "flac"

    def test_hi_mp3_url_returns_hi_mp3(self):
        mock_src = _mock_source(QualityTier.HI_MP3)
        with patch("backend.app.api.quality.find_source_for_url", return_value=mock_src):
            resp = client.post("/api/quality", json={"urls": [_SC_URL]})
        assert resp.status_code == 200
        assert resp.json()["results"][_SC_URL] == "hi_mp3"

    def test_unrecognised_url_returns_unknown(self):
        with patch("backend.app.api.quality.find_source_for_url", return_value=None):
            resp = client.post("/api/quality", json={"urls": [_UNKNOWN_URL]})
        assert resp.status_code == 200
        assert resp.json()["results"][_UNKNOWN_URL] == "unknown"

    def test_probe_exception_returns_unknown_not_500(self):
        mock_src = MagicMock()
        mock_src.probe_quality.side_effect = RuntimeError("unexpected crash")
        with patch("backend.app.api.quality.find_source_for_url", return_value=mock_src):
            resp = client.post("/api/quality", json={"urls": [_YT_URL]})
        assert resp.status_code == 200
        assert resp.json()["results"][_YT_URL] == "unknown"

    def test_batch_returns_all_urls(self):
        def fake_find(url):
            if "youtube" in url:
                return _mock_source(QualityTier.STANDARD)
            if "soundcloud" in url:
                return _mock_source(QualityTier.HI_MP3)
            return None

        with patch("backend.app.api.quality.find_source_for_url", side_effect=fake_find):
            resp = client.post("/api/quality", json={"urls": [_YT_URL, _SC_URL, _UNKNOWN_URL]})

        assert resp.status_code == 200
        data = resp.json()["results"]
        assert set(data.keys()) == {_YT_URL, _SC_URL, _UNKNOWN_URL}
        assert data[_YT_URL] == "standard"
        assert data[_SC_URL] == "hi_mp3"
        assert data[_UNKNOWN_URL] == "unknown"

    def test_urls_truncated_at_25(self):
        urls = [f"https://www.youtube.com/watch?v={i}" for i in range(30)]
        mock_src = _mock_source(QualityTier.STANDARD)
        with patch("backend.app.api.quality.find_source_for_url", return_value=mock_src):
            resp = client.post("/api/quality", json={"urls": urls})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 25
