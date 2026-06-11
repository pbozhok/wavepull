from __future__ import annotations
import asyncio
import shutil
import urllib.parse
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse

from ..sources import _pool, find_source_for_url
from ..sources.base import NotDownloadableError, SourceUnavailableError

router = APIRouter()


async def _run_prepare(source, url: str) -> tuple[str, str, str]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_pool, source.prepare_download, url)


@router.get("/download")
async def download(
    url: str = Query(..., description="Source page URL from a search result"),
    background_tasks: BackgroundTasks = None,
):
    if not url:
        raise HTTPException(status_code=400, detail="url parameter is required")

    source = find_source_for_url(url)
    if source is None:
        raise HTTPException(
            status_code=422,
            detail="Unsupported URL. Supported sources: YouTube, SoundCloud, Bandcamp",
        )

    try:
        file_path, mime, filename = await _run_prepare(source, url)
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
    encoded_name = urllib.parse.quote(filename, safe=" -()")
    disposition = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded_name}'

    return FileResponse(
        path=file_path,
        media_type=mime,
        filename=filename,
        headers={"Content-Disposition": disposition},
    )
