from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.result import DownloadMetadata, SourceResult


class SourceUnavailableError(Exception):
    """Platform unreachable, rate-limited, or temporarily failing."""


class UnsupportedURLError(Exception):
    """URL does not belong to this source."""


class NotDownloadableError(Exception):
    """Track exists but cannot be downloaded (DRM, geo-block, private)."""


class SourcePlugin(ABC):
    name: str
    display_name: str

    @abstractmethod
    def can_handle_url(self, url: str) -> bool:
        """Pure predicate — no network calls."""

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[SourceResult]:
        """Text search. Returns [] on empty results, raises SourceUnavailableError on failure."""

    @abstractmethod
    def resolve_url(self, url: str) -> SourceResult:
        """Resolve a direct URL to a single result."""

    @abstractmethod
    def prepare_download(
        self,
        url: str,
        metadata: "DownloadMetadata | None" = None,
    ) -> tuple[str, str, str]:
        """Download audio to a temp directory. Interface v2.

        When metadata is provided, embed title/artist/album/year into the file.
        Returns (file_path, mime_type, suggested_filename).
        Caller must delete the parent temp directory after use.
        """
