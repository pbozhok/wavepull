from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
from fastapi.staticfiles import StaticFiles
from .api.search import router as search_router
from .api.download import router as download_router
from .api.quality import router as quality_router
from .api.genre import router as genre_router

app = FastAPI(title="Wavepull")

app.include_router(search_router, prefix="/api")
app.include_router(download_router, prefix="/api")
app.include_router(quality_router, prefix="/api")
app.include_router(genre_router, prefix="/api")

_frontend = Path(__file__).parent.parent.parent / "frontend"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")
