from __future__ import annotations
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from .base import SourcePlugin, UnsupportedURLError
from .youtube import YouTubeSource
from .soundcloud import SoundCloudSource
from .bandcamp import BandcampSource
from ..models.result import SearchResponse, SourceResult

SOURCES: list[SourcePlugin] = [
    YouTubeSource(),
    SoundCloudSource(),
    BandcampSource(),
]

_pool = ThreadPoolExecutor(max_workers=6)


_SEARCH_UNSUPPORTED = {"bandcamp"}  # text search not supported for these sources


def parallel_search(query: str, limit: int = 5) -> SearchResponse:
    results: list[SourceResult] = []
    errors: list[str] = []

    searchable = [src for src in SOURCES if src.name not in _SEARCH_UNSUPPORTED]
    skipped = [src for src in SOURCES if src.name in _SEARCH_UNSUPPORTED]

    for src in skipped:
        errors.append(
            f"{src.display_name}: text search unavailable — paste a {src.display_name} URL directly"
        )

    futures = {_pool.submit(src.search, query, limit): src for src in searchable}
    for future in concurrent.futures.as_completed(futures, timeout=25):
        src = futures[future]
        try:
            results.extend(future.result())
        except Exception as exc:
            errors.append(f"{src.display_name} unavailable: {str(exc)[:120]}")

    return SearchResponse(query=query, results=results, source_errors=errors)


def resolve_single_url(url: str) -> SearchResponse:
    for src in SOURCES:
        if src.can_handle_url(url):
            result = src.resolve_url(url)
            return SearchResponse(query=url, results=[result], source_errors=[])
    raise UnsupportedURLError(f"No source handles: {url}")


def find_source_for_url(url: str) -> SourcePlugin | None:
    for src in SOURCES:
        if src.can_handle_url(url):
            return src
    return None
