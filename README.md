# Wavepull

Self-hosted music search and download. Search by song name, artist, or direct URL — get the best available quality with one click.

Supported sources: **YouTube**, **SoundCloud**, **Bandcamp**

## Requirements

- Python 3.11+
- Internet access

## Quickstart

```bash
git clone https://github.com/pbozhok/wavepull.git
cd wavepull
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
uvicorn backend.app.main:app
```

Open [http://localhost:8000](http://localhost:8000).

## Usage

| Input | Example |
|---|---|
| Song name | `Burial - Archangel` |
| Name only | `Aphex Twin Xtal` |
| Direct URL | `https://soundcloud.com/…` |

Results from all three sources are shown together. Click **DL** to download at the highest available quality. Click a result to open it on the source site.

## Running tests

```bash
pytest
```

## Adding a source

1. Create `backend/app/sources/mysource.py` implementing the `SourcePlugin` ABC from `base.py`
2. Register it in `backend/app/sources/__init__.py`

No other changes required.
