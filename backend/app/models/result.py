from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class QualityTier(str, Enum):
    FLAC = "flac"
    HI_MP3 = "hi_mp3"
    STANDARD = "standard"
    UNKNOWN = "unknown"


@dataclass
class DownloadMetadata:
    title: str
    artist: str
    album: str = ""
    year: str = ""
    genre: str = ""
    thumbnail_url: str = ""


@dataclass
class SourceResult:
    id: str
    title: str
    artist: str
    source: Literal["youtube", "soundcloud", "bandcamp"]
    thumbnail_url: str | None
    source_page_url: str
    duration_seconds: int | None
    quality_tier: QualityTier = QualityTier.UNKNOWN


@dataclass
class SearchResponse:
    query: str
    results: list[SourceResult] = field(default_factory=list)
    source_errors: list[str] = field(default_factory=list)
