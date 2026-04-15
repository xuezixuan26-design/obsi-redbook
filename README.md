# Obsi Redbook

Clip Xiaohongshu (Rednote) posts and public WeChat articles into Obsidian-friendly Markdown.

This repository now has two usable surfaces:

- A Python workflow for batch import, optional transcription, and note analysis
- A Chrome extension MVP for in-browser capture, preview, copy, download, and optional Obsidian handoff

## Features

### Python Workflow

- Fetch Xiaohongshu posts with exported browser cookies
- Fetch public WeChat articles without browser automation
- Normalize both sources into a shared JSON shape
- Render concise Markdown notes for Obsidian
- Optionally extract and transcribe video audio
- Batch import mixed URL lists
- Generate deterministic local analysis reports from saved notes

### Chrome Extension

- Works on Xiaohongshu post pages and public WeChat article pages
- Extracts content directly from the open page
- Shows a quick preview in the popup
- Copies Markdown to clipboard
- Downloads Markdown or JSON
- Optionally opens an `obsidian://` link when a vault name is configured

## Repository Layout

```text
.
├── AGENTS.md
├── LICENSE
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── pytest.ini
├── urls.txt
├── extension/
│   ├── manifest.json
│   ├── shared.js
│   ├── content.js
│   ├── popup.html
│   ├── popup.css
│   ├── popup.js
│   ├── options.html
│   ├── options.css
│   └── options.js
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

## Python Setup

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

## Chrome Extension Setup

1. Open Chrome and go to `chrome://extensions`
2. Turn on `Developer mode`
3. Click `Load unpacked`
4. Select the `extension/` folder from this repository

After installation:

- Open a Xiaohongshu post or public WeChat article
- Click the extension icon
- Refresh the popup preview
- Copy or download the generated note
- If you configure a vault name in the extension options, use `Send To Obsidian`

## Chrome Extension Publishing Prep

This repository now includes the basic assets needed for broader sharing:

- extension icons in `extension/icons/`
- Chrome Web Store draft copy in [STORE_LISTING.md](./STORE_LISTING.md)
- privacy statement in [PRIVACY.md](./PRIVACY.md)
- extension-specific notes in [extension/README.md](./extension/README.md)

For the next publishing step, you can:

1. Load the extension locally from `extension/`
2. Test capture on Xiaohongshu and WeChat pages
3. Zip the `extension/` folder for submission packaging
4. Reuse the draft text from `STORE_LISTING.md` when creating the Chrome Web Store listing
5. Follow [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md) and [CHROME_STORE_SUBMISSION.md](./CHROME_STORE_SUBMISSION.md) during submission

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

### Analyze Saved Notes

```powershell
python scripts/analyze_notes.py `
  --notes-dir data/notes `
  --output data/notes/_analysis.md
```

## Security Notes

- Never commit `.env`, cookies, API keys, or local vault paths
- `data/cookies.txt` must remain local-only
- Generated data in `data/raw/`, `data/media/`, and `data/notes/` is ignored by default

## Testing

Run all Python tests:

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

## License

MIT
