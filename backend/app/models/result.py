from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class DownloadMetadata:
    title: str
    artist: str
    album: str = ""
    year: str = ""


@dataclass
class SourceResult:
    id: str
    title: str
    artist: str
    source: Literal["youtube", "soundcloud", "bandcamp"]
    thumbnail_url: str | None
    source_page_url: str
    duration_seconds: int | None


@dataclass
class SearchResponse:
    query: str
    results: list[SourceResult] = field(default_factory=list)
    source_errors: list[str] = field(default_factory=list)
