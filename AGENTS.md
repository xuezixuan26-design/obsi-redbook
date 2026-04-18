# AGENTS.md

## Project Overview

This repository is a Codex-native Python project for importing Xiaohongshu (Rednote) posts into Obsidian-friendly Markdown notes. The architecture separates deterministic ingestion from higher-level analysis so that DeerFlow or another agent framework can be added later without rewriting the core importer.

## Structure

- `scripts/fetch_xhs.py`: Network access, cookie loading, HTML fetch, embedded state parsing, and raw payload export.
- `scripts/transcribe_audio.py`: Optional media audio extraction via `ffmpeg` and transcript-sidecar loading.
- `scripts/render_note.py`: Jinja2-based Markdown rendering and note file writing.
- `scripts/batch_import.py`: End-to-end importer for raw HTML files or live fetch targets.
- `scripts/analyze_notes.py`: Note clustering, summarization, prioritization, and analysis report generation.
- `templates/note.md.j2`: Obsidian note template.
- `templates/analysis.md.j2`: Analysis report template.
- `data/raw/`: Saved HTML and normalized JSON payloads.
- `data/media/`: Downloaded media and optional extracted audio.
- `data/notes/`: Rendered Markdown notes for Obsidian.
- `data/analysis/`: Generated analysis reports.
- `tests/`: Minimal parser and renderer tests.

## Python Version

- Python `3.11+`

## Conventions

- Keep all network requests isolated to `fetch_xhs.py`.
- Keep all Markdown rendering isolated to `render_note.py`.
- Keep all transcription logic isolated to `transcribe_audio.py`.
- Use UTF-8 for all text files.
- Prefer deterministic parsing and file output over agent-driven logic in the ingestion pipeline.
- Treat DeerFlow as an analysis-layer orchestrator, not as the fetch/render runtime.

## Common Commands

Install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run tests:

```powershell
pytest
```

Import a saved HTML export:

```powershell
python scripts\batch_import.py --html data\raw\sample_note.html
```

Fetch a live note using exported cookies:

```powershell
python scripts\fetch_xhs.py --url https://www.xiaohongshu.com/explore/NOTE_ID --cookies cookies.txt
```

Render a Markdown note from normalized JSON:

```powershell
python scripts\render_note.py --input data\raw\note_payload.json
```

Analyze imported notes:

```powershell
python scripts\analyze_notes.py --notes-dir data\notes --output data\analysis\latest-analysis.md
```

## Testing Notes

- `tests/test_parse_state.py` covers embedded state extraction and normalization.
- `tests/test_render_note.py` covers Markdown rendering and frontmatter output.

## Codex Guidance

- Make additive changes where possible.
- Do not add browser automation.
- Do not introduce backend-service dependencies for ingestion.
- If you add DeerFlow later, wire it into `scripts/analyze_notes.py` or a new `workflows/` directory without changing the fetch/render contracts.
