# xhs-codex-importer

A Codex-native Python workflow for importing Xiaohongshu (Rednote) posts and public WeChat articles into structured Markdown notes for Obsidian.

## What It Does

- Fetches Xiaohongshu post pages using exported browser cookies
- Fetches public WeChat article pages without browser automation
- Normalizes both sources into a shared JSON shape
- Renders concise, Obsidian-friendly Markdown notes
- Optionally extracts and transcribes video audio
- Batch imports mixed URL lists
- Generates deterministic local analysis reports from saved notes

## Design Principles

- Python `3.11+`
- No browser automation
- No backend service dependency
- Source fetching isolated to source-specific fetch scripts
- Markdown rendering isolated to `scripts/render_note.py`
- Transcription isolated to `scripts/transcribe_audio.py`
- Simple local analysis first

## Repository Layout

```text
.
├── AGENTS.md
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── pytest.ini
├── urls.txt
├── scripts/
│   ├── fetch_xhs.py
│   ├── fetch_wechat.py
│   ├── transcribe_audio.py
│   ├── render_note.py
│   ├── batch_import.py
│   ├── analyze_notes.py
│   └── local_env.py
├── templates/
│   ├── note.md.j2
│   └── analysis.md.j2
├── data/
│   ├── raw/
│   ├── media/
│   └── notes/
└── tests/
    ├── fixtures/
    ├── test_parse_state.py
    ├── test_fetch_wechat.py
    ├── test_render_note.py
    ├── test_batch_import.py
    ├── test_transcribe_audio.py
    └── test_analyze_notes.py
```

## Setup

1. Create a virtual environment:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` if you want local defaults:

   ```powershell
   Copy-Item .env.example .env
   ```

4. To write notes directly into your Obsidian vault, configure:

   ```env
   OBSIDIAN_VAULT_PATH=C:\Users\Lenovo\Documents\Obsidian Vault
   OBSIDIAN_IMPORT_SUBDIR=Inbox\Xiaohongshu
   ```

## Cookies

For Xiaohongshu fetching, place exported cookies in `data/cookies.txt`.

Supported formats:

- Netscape cookie export format
- Raw cookie string such as `a=1; web_session=...; xsecappid=...`

## Usage

### Fetch One Xiaohongshu Post

```powershell
python scripts/fetch_xhs.py `
  --url "https://www.xiaohongshu.com/explore/POST_ID"
```

### Fetch One WeChat Article

```powershell
python scripts/fetch_wechat.py `
  --url "https://mp.weixin.qq.com/s?__biz=...&mid=...&sn=..."
```

### Render One Note

```powershell
python scripts/render_note.py `
  --input data/raw/post.json
```

If `OBSIDIAN_VAULT_PATH` is set, notes are written into your vault import folder by default. Otherwise they go to `data/notes/`.

### Batch Import Mixed URLs

Put one URL per line in `urls.txt`. Empty lines and lines beginning with `#` are ignored.

```powershell
python scripts/batch_import.py `
  --input-file urls.txt `
  --cookies data/cookies.txt
```

This pipeline will:

1. Detect the source type from each URL
2. Fetch and normalize the item
3. Optionally transcribe video when enabled
4. Render the final Markdown note
5. Print a batch summary with success, failure, and note paths

Enable transcription for video items:

```powershell
python scripts/batch_import.py `
  --input-file urls.txt `
  --cookies data/cookies.txt `
  --transcribe-video `
  --transcription-backend local-placeholder
```

### Optional Audio Extraction And Transcription

```powershell
python scripts/transcribe_audio.py `
  --source data/media/sample.mp4
```

Or from a direct media URL:

```powershell
python scripts/transcribe_audio.py `
  --source "https://example.com/sample.mp4" `
  --media-dir data/media
```

Notes:

- Install `ffmpeg` and ensure it is on `PATH`
- The default backend is a local placeholder
- Future real backends can be added without changing fetch or render logic

### Analyze Saved Notes

```powershell
python scripts/analyze_notes.py `
  --notes-dir data/notes `
  --output data/notes/_analysis.md
```

The analysis report includes:

- recurring themes
- frequently mentioned products or topics
- possible signals worth deeper research
- a compact summary for the user

## Normalized Data Shape

The fetchers normalize content into a shared structure like:

```json
{
  "url": "https://www.xiaohongshu.com/explore/abc123",
  "note_id": "abc123",
  "title": "Example title",
  "author": {
    "name": "Author",
    "user_id": "user123",
    "profile_url": ""
  },
  "content": "Body text",
  "tags": ["travel", "shanghai"],
  "images": ["https://..."],
  "video_url": null,
  "published_at": "2024-06-01T12:00:00+00:00",
  "source_type": "xhs",
  "raw_state_path": "data/raw/abc123.json"
}
```

WeChat articles use the same general shape, usually with empty `tags` and article images extracted into `images`.

## Testing

Run all tests:

```powershell
python -m pytest
```

Current coverage includes:

- Xiaohongshu parser fixtures
- WeChat article parser fixtures
- batch orchestration helpers
- Markdown rendering logic
- transcription path and command helpers
- note analysis parsing and summarization

## Security Notes

- Never commit `.env`, cookies, API keys, or local vault paths
- `data/cookies.txt` must remain local-only
- Generated data in `data/raw/`, `data/media/`, and `data/notes/` is ignored by default
