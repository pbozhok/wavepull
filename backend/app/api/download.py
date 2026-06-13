from __future__ import annotations
import asyncio
import re
import shutil
import urllib.parse
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from ..models.result import DownloadMetadata
from ..sources import _pool, find_source_for_url
from ..sources.base import NotDownloadableError, SourceUnavailableError

router = APIRouter()


class DownloadRequest(BaseModel):
    url: str
    title: str
    artist: str
    album: str = ""
    year: str = ""
    genre: str = ""
    thumbnail_url: str = ""

    @field_validator("title", "artist")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()

    @field_validator("year")
    @classmethod
    def year_format(cls, v: str) -> str:
        if v and not re.fullmatch(r"\d{4}", v):
            raise ValueError("must be a 4-digit year or empty")
        return v


async def _run_prepare(source, url: str, metadata: DownloadMetadata) -> tuple[str, str, str]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_pool, source.prepare_download, url, metadata)


@router.post("/download")
async def download(
    body: DownloadRequest,
    background_tasks: BackgroundTasks = None,
):
    source = find_source_for_url(body.url)
    if source is None:
        raise HTTPException(
            status_code=422,
            detail="Unsupported URL. Supported sources: YouTube, SoundCloud, Bandcamp",
        )

    metadata = DownloadMetadata(
        title=body.title,
        artist=body.artist,
        album=body.album,
        year=body.year,
        genre=body.genre.strip(),
        thumbnail_url=body.thumbnail_url,
    )

    try:
        file_path, mime, filename = await _run_prepare(source, body.url, metadata)
    except NotDownloadableError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"This track cannot be downloaded: {exc}",
        )
    except SourceUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="Source temporarily unavailable. Please try again later.",
        )

    tmp_dir = str(Path(file_path).parent)
    background_tasks.add_task(shutil.rmtree, tmp_dir, True)

    ascii_name = filename.encode("ascii", errors="replace").decode("ascii").replace("?", "_")
    encoded_name = urllib.parse.quote(filename, safe="-()")
    disposition = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded_name}'

    return FileResponse(
        path=file_path,
        media_type=mime,
        filename=filename,
        headers={"Content-Disposition": disposition},
    )
