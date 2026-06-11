from __future__ import annotations
import re

import yt_dlp

from .base import (
    NotDownloadableError,
    SourcePlugin,
    SourceUnavailableError,
    UnsupportedURLError,
)
from .youtube import _YDL_BASE_OPTS, _make_result, _ydl_prepare_download
from ..models.result import SourceResult

_URL_RE = re.compile(r"https?://(www\.)?soundcloud\.com/")


class SoundCloudSource(SourcePlugin):
    name = "soundcloud"
    display_name = "SoundCloud"

    def can_handle_url(self, url: str) -> bool:
        return bool(_URL_RE.match(url))

    def search(self, query: str, limit: int = 5) -> list[SourceResult]:
        opts = {**_YDL_BASE_OPTS}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"scsearch{limit}:{query}", download=False)
            entries = info.get("entries") or []
            results = []
            for e in entries:
                if not e:
                    continue
                r = _make_result(e, "soundcloud")
                results.append(r)
            return results
        except yt_dlp.utils.DownloadError as exc:
            raise SourceUnavailableError(str(exc)) from exc

    def resolve_url(self, url: str) -> SourceResult:
        if not self.can_handle_url(url):
            raise UnsupportedURLError(f"Not a SoundCloud URL: {url}")
        try:
            with yt_dlp.YoutubeDL(_YDL_BASE_OPTS) as ydl:
                info = ydl.extract_info(url, download=False)
            return _make_result(info, "soundcloud")
        except yt_dlp.utils.DownloadError as exc:
            raise SourceUnavailableError(str(exc)) from exc

    def prepare_download(self, url: str) -> tuple[str, str, str]:
        return _ydl_prepare_download(url, self.name)
