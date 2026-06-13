from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel

from ..services.genre import GenreService

router = APIRouter()


class GenreRequest(BaseModel):
    artist: str
    title: str


class GenreResponse(BaseModel):
    genre: str | None


@router.post("/genre", response_model=GenreResponse)
async def get_genre(body: GenreRequest) -> GenreResponse:
    genre = GenreService().lookup(body.artist, body.title)
    return GenreResponse(genre=genre)
