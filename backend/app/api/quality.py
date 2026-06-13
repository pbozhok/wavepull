from __future__ import annotations
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..sources import _pool, find_source_for_url

router = APIRouter()

_PROBE_TIMEOUT = 10.0
_MAX_URLS = 25


class QualityRequest(BaseModel):
    urls: list[str]


def _probe_one(url: str) -> tuple[str, str]:
    source = find_source_for_url(url)
    if source is None:
        return url, "unknown"
    tier = source.probe_quality(url)
    return url, tier.value


@router.post("/quality")
async def quality(body: QualityRequest):
    if not body.urls:
        raise HTTPException(status_code=400, detail="urls must be a non-empty list")

    urls = body.urls[:_MAX_URLS]
    loop = asyncio.get_event_loop()

    async def probe(url: str) -> tuple[str, str]:
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(_pool, _probe_one, url),
                timeout=_PROBE_TIMEOUT,
            )
        except Exception:
            return url, "unknown"

    pairs = await asyncio.gather(*[probe(u) for u in urls])
    return {"results": dict(pairs)}
