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

## Desktop shortcut (Windows)

After completing the Quickstart, create a one-click desktop icon:

```powershell
powershell -ExecutionPolicy Bypass -File launcher\install-shortcut.ps1
```

This places a **WavePull** shortcut on your Desktop. Double-clicking it starts the server (if not already running) and opens the app in your browser. Run the command again if you move the project folder.

## Genre enrichment (optional)

When you click **DL**, Wavepull can automatically suggest the genre of the track before you download it. You can confirm the suggestion, edit it, or clear it — the genre is then written into the downloaded file's metadata tags.

This feature requires a free Last.fm API key:

1. Register at [last.fm/api/account/create](https://www.last.fm/api/account/create) and copy your **API key**.
2. Set the environment variable before starting the server:

   ```powershell
   $env:LASTFM_API_KEY = "your_api_key"
   ```

   Or copy `.env.example` to `.env`, fill in the value, and load it before running `uvicorn`.

Without a key the genre field is simply left empty and editable — downloads work normally.

## Usage

| Input | Example |
|---|---|
| Song name | `Burial - Archangel` |
| Name only | `Aphex Twin Xtal` |
| Direct URL | `https://soundcloud.com/…` |

Results from all three sources are shown together. Click **DL** to download at the highest available quality. A metadata panel opens where you can review and edit the title, artist, album, year, and genre before the file is saved. Click a result to open it on the source site.

## Running tests

```bash
pytest
```

## Adding a source

1. Create `backend/app/sources/mysource.py` implementing the `SourcePlugin` ABC from `base.py`
2. Register it in `backend/app/sources/__init__.py`

No other changes required.
