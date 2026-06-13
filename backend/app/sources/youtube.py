from __future__ import annotations
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yt_dlp
from mutagen import File as MutagenFile

from .base import (
    NotDownloadableError,
    SourcePlugin,
    SourceUnavailableError,
    UnsupportedURLError,
)
from ..models.result import DownloadMetadata, QualityTier, SourceResult

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


def _write_metadata(path: str, metadata: DownloadMetadata) -> None:
    audio = MutagenFile(path, easy=True)
    if audio is None:
        return
    if audio.tags is None:
        try:
            audio.add_tags()
        except Exception:
            pass
    if metadata.title:
        audio["title"] = [metadata.title]
    if metadata.artist:
        audio["artist"] = [metadata.artist]
    if metadata.album:
        audio["album"] = [metadata.album]
    if metadata.year:
        audio["date"] = [metadata.year]
    audio.save()


def _ydl_probe_quality(url: str) -> QualityTier:
    """Probe available audio quality for a URL without downloading.
    Returns QualityTier. Never raises.
    """
    try:
        with yt_dlp.YoutubeDL(_YDL_BASE_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
        formats = info.get("formats") or []
        audio_fmts = [
            f for f in formats
            if f.get("acodec") not in (None, "none") or f.get("ext") in _MIME_MAP
        ]
        if any(f.get("ext") == "flac" for f in audio_fmts):
            return QualityTier.FLAC
        if any((f.get("abr") or 0) >= 320 for f in audio_fmts):
            return QualityTier.HI_MP3
        if audio_fmts:
            return QualityTier.STANDARD
        return QualityTier.UNKNOWN
    except Exception:
        return QualityTier.UNKNOWN


def _ydl_prepare_download(
    url: str,
    source_name: str,
    metadata: DownloadMetadata | None = None,
) -> tuple[str, str, str]:
    tmpdir = tempfile.mkdtemp(prefix="wavepull_")
    opts = {
        **_YDL_BASE_OPTS,
        "format": "bestaudio[ext=flac]/bestaudio[ext=mp3]/bestaudio",
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

        if ext not in ("flac", "mp3"):
            mp3_path = audio_file.with_suffix(".mp3")
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(audio_file), "-q:a", "0", str(mp3_path)],
                    capture_output=True,
                    check=True,
                )
                audio_file.unlink()
                audio_file = mp3_path
                ext = "mp3"
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass  # ffmpeg unavailable; keep original format

        mime = _MIME_MAP.get(ext, "audio/mpeg")

        if metadata:
            title = metadata.title.replace("/", "-")[:80]
            _write_metadata(str(audio_file), metadata)
            filename = f"{title}.{ext}"
        else:
            title = (info.get("title") or "track").replace("/", "-")[:80]
            artist = (info.get("uploader") or info.get("channel") or "Unknown").replace("/", "-")[:50]
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

    def prepare_download(
        self,
        url: str,
        metadata: DownloadMetadata | None = None,
    ) -> tuple[str, str, str]:
        return _ydl_prepare_download(url, self.name, metadata)

    def probe_quality(self, url: str) -> QualityTier:
        return _ydl_probe_quality(url)
