from __future__ import annotations
import hashlib
import re

import yt_dlp

from .base import (
    SourcePlugin,
    SourceUnavailableError,
    UnsupportedURLError,
)
from .youtube import _YDL_BASE_OPTS, _ydl_prepare_download, _ydl_probe_quality
from ..models.result import DownloadMetadata, QualityTier, SourceResult

_URL_RE = re.compile(r"https?://[^.]+\.bandcamp\.com/")


class BandcampSource(SourcePlugin):
    name = "bandcamp"
    display_name = "Bandcamp"

    def can_handle_url(self, url: str) -> bool:
        return bool(_URL_RE.match(url))

    def search(self, query: str, limit: int = 5) -> list[SourceResult]:
        # Bandcamp's search page requires JavaScript (Cloudflare challenge) and
        # cannot be scraped server-side. Text search returns no results.
        # Paste a Bandcamp track URL directly to resolve and download it.
        return []

    def resolve_url(self, url: str) -> SourceResult:
        if not self.can_handle_url(url):
            raise UnsupportedURLError(f"Not a Bandcamp URL: {url}")
        try:
            with yt_dlp.YoutubeDL(_YDL_BASE_OPTS) as ydl:
                info = ydl.extract_info(url, download=False)
            title = info.get("title") or "Unknown"
            artist = info.get("uploader") or info.get("artist") or "Unknown"
            page_url = info.get("webpage_url") or url
            thumbnail = info.get("thumbnail")
            duration = info.get("duration")
            result_id = hashlib.sha256(page_url.encode()).hexdigest()[:16]
            return SourceResult(
                id=result_id,
                title=title,
                artist=artist,
                source="bandcamp",
                thumbnail_url=thumbnail,
                source_page_url=page_url,
                duration_seconds=int(duration) if duration else None,
            )
        except yt_dlp.utils.DownloadError as exc:
            raise SourceUnavailableError(str(exc)) from exc

    def prepare_download(
        self,
        url: str,
        metadata: DownloadMetadata | None = None,
    ) -> tuple[str, str, str]:
        return _ydl_prepare_download(url, self.name, metadata)

    def probe_quality(self, url: str) -> QualityTier:
        return _ydl_probe_quality(url)
