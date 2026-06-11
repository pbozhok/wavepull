from __future__ import annotations
import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path

import yt_dlp

from .base import (
    NotDownloadableError,
    SourcePlugin,
    SourceUnavailableError,
    UnsupportedURLError,
)
from ..models.result import SourceResult

_URL_RE = re.compile(r"https?://(www\.)?(youtube\.com|youtu\.be)/")

_MIME_MAP = {
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "ogg": "audio/ogg",
    "opus": "audio/opus",
    "webm": "audio/webm",
    "flac": "audio/flac",
}

_YDL_BASE_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "socket_timeout": 30,
    "skip_unavailable_fragments": True,
}


def _make_result(info: dict, source: str) -> SourceResult:
    title = info.get("title") or "Unknown"
    artist = info.get("uploader") or info.get("channel") or "Unknown"
    page_url = info.get("webpage_url") or info.get("url") or ""
    video_id = info.get("id")
    if source == "youtube" and video_id:
        # maxresdefault 404s on many videos; hqdefault always exists
        thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    else:
        thumbnail = info.get("thumbnail")
    duration = info.get("duration")
    result_id = hashlib.sha256(page_url.encode()).hexdigest()[:16]
    return SourceResult(
        id=result_id,
        title=title,
        artist=artist,
        source=source,  # type: ignore[arg-type]
        thumbnail_url=thumbnail,
        source_page_url=page_url,
        duration_seconds=int(duration) if duration else None,
    )


def _ydl_prepare_download(url: str, source_name: str) -> tuple[str, str, str]:
    tmpdir = tempfile.mkdtemp(prefix="wavepull_")
    opts = {
        **_YDL_BASE_OPTS,
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmpdir, "audio.%(ext)s"),
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

        files = list(Path(tmpdir).glob("*"))
        if not files:
            raise NotDownloadableError("Download produced no output file")

        audio_file = files[0]
        ext = audio_file.suffix.lstrip(".")
        title = (info.get("title") or "track").replace("/", "-")[:80]
        artist = (info.get("uploader") or info.get("channel") or "Unknown").replace("/", "-")[:50]
        mime = _MIME_MAP.get(ext, "audio/mpeg")
        filename = f"{artist} - {title}.{ext}"
        return str(audio_file), mime, filename
    except NotDownloadableError:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
    except yt_dlp.utils.DownloadError as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        msg = str(exc).lower()
        if any(x in msg for x in ("geo", "restricted", "private", "unavailable", "removed", "drm")):
            raise NotDownloadableError(str(exc)) from exc
        raise SourceUnavailableError(str(exc)) from exc
    except Exception as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise SourceUnavailableError(str(exc)) from exc


class YouTubeSource(SourcePlugin):
    name = "youtube"
    display_name = "YouTube"

    def can_handle_url(self, url: str) -> bool:
        return bool(_URL_RE.match(url))

    def search(self, query: str, limit: int = 5) -> list[SourceResult]:
        opts = {**_YDL_BASE_OPTS, "extract_flat": True}
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            entries = info.get("entries") or []
            return [_make_result(e, "youtube") for e in entries if e]
        except yt_dlp.utils.DownloadError as exc:
            raise SourceUnavailableError(str(exc)) from exc

    def resolve_url(self, url: str) -> SourceResult:
        if not self.can_handle_url(url):
            raise UnsupportedURLError(f"Not a YouTube URL: {url}")
        try:
            with yt_dlp.YoutubeDL(_YDL_BASE_OPTS) as ydl:
                info = ydl.extract_info(url, download=False)
            return _make_result(info, "youtube")
        except yt_dlp.utils.DownloadError as exc:
            raise SourceUnavailableError(str(exc)) from exc

    def prepare_download(self, url: str) -> tuple[str, str, str]:
        return _ydl_prepare_download(url, self.name)
