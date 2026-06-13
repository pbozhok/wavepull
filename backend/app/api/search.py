from __future__ import annotations
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..sources import _pool, parallel_search, resolve_single_url
from ..sources.base import UnsupportedURLError

router = APIRouter()


class SearchRequest(BaseModel):
    query: str


@router.post("/search")
async def search(body: SearchRequest):
    q = body.query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    loop = asyncio.get_event_loop()

    if q.startswith("http://") or q.startswith("https://"):
        try:
            response = await loop.run_in_executor(_pool, resolve_single_url, q)
        except UnsupportedURLError:
            raise HTTPException(
                status_code=422,
                detail="Unsupported URL. Supported sources: YouTube, SoundCloud, Bandcamp",
            )
    else:
        response = await loop.run_in_executor(_pool, parallel_search, q)

    return {
        "query": response.query,
        "results": [
            {
                "id": r.id,
                "title": r.title,
                "artist": r.artist,
                "source": r.source,
                "thumbnail_url": r.thumbnail_url,
                "source_page_url": r.source_page_url,
                "duration_seconds": r.duration_seconds,
                "quality_tier": r.quality_tier.value,
            }
            for r in response.results
        ],
        "source_errors": response.source_errors,
    }
