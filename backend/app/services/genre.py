from __future__ import annotations
import os
import re

import requests

_BASE_URL = "https://ws.audioscrobbler.com/2.0/"

_MULTI_ARTIST_RE = re.compile(
    r"\s*[&,]\s*|\s+feat\.?\s+|\s+ft\.?\s+|\s+vs\.?\s+|\s+x\s+",
    re.IGNORECASE,
)

_SKIP_TAGS = {
    # personal / subjective
    "seen live", "favorites", "favourite", "my music", "love",
    "best of", "love it", "all time favorites", "check out",
    # nationality / location (common Last.fm tags, not genres)
    "british", "uk", "usa", "american", "german", "french",
    "swedish", "canadian", "australian", "norwegian", "irish",
    "scottish", "welsh", "italian", "japanese", "korean",
}


def _api_key() -> str | None:
    return os.getenv("LASTFM_API_KEY", "").strip() or None


def _first_tag(tags: list) -> str | None:
    for tag in tags:
        name = (tag.get("name") or "").strip()
        if name and name.lower() not in _SKIP_TAGS:
            return name
    return None


class GenreService:
    def lookup(self, artist: str, title: str) -> str | None:
        try:
            key = _api_key()
            if key is None:
                return None

            primary = _MULTI_ARTIST_RE.split(artist)[0].strip()
            is_multi = primary != artist

            # 1. Track-level tags (most specific)
            genre = self._track_tags(key, artist, title)
            if genre:
                return genre

            # 2. Artist-level tags (reliable fallback)
            genre = self._artist_tags(key, artist)
            if genre:
                return genre

            # 3. Primary artist only — handles "A & B", "A feat. B", etc.
            if is_multi:
                genre = self._artist_tags(key, primary)

            return genre
        except Exception:
            return None

    def _track_tags(self, key: str, artist: str, title: str) -> str | None:
        resp = requests.get(
            _BASE_URL,
            params={
                "method": "track.getTopTags",
                "artist": artist,
                "track": title,
                "api_key": key,
                "autocorrect": "1",
                "format": "json",
            },
            timeout=5,
        )
        data = resp.json()
        if "error" in data:
            return None
        return _first_tag(data.get("toptags", {}).get("tag", []))

    def _artist_tags(self, key: str, artist: str) -> str | None:
        resp = requests.get(
            _BASE_URL,
            params={
                "method": "artist.getTopTags",
                "artist": artist,
                "api_key": key,
                "autocorrect": "1",
                "format": "json",
            },
            timeout=5,
        )
        data = resp.json()
        if "error" in data:
            return None
        return _first_tag(data.get("toptags", {}).get("tag", []))
