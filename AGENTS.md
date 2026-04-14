# AGENTS.md

## Goal

This repository is a Codex-native Python workflow for importing Xiaohongshu (Rednote) posts and public WeChat articles into structured Markdown notes for Obsidian. The pipeline fetches source pages, normalizes their data, optionally transcribes video audio, renders Markdown notes, and analyzes note collections locally.

## Structure

- `scripts/`: executable workflow modules.
  - `fetch_xhs.py`: source-specific Xiaohongshu fetching, cookies, and normalization.
  - `fetch_wechat.py`: source-specific public WeChat article fetching and normalization.
  - `render_note.py`: the only place where Markdown rendering logic belongs.
  - `transcribe_audio.py`: the only place where media download, audio extraction, and transcription logic belongs.
  - `batch_import.py`: orchestration for batch fetch -> optional transcription -> render.
  - `analyze_notes.py`: deterministic local analysis of generated Markdown notes.
- `templates/`: Jinja2 templates for rendered notes and analysis reports.
- `data/`: local working data only.
  - `raw/`: fetched HTML and normalized JSON.
  - `media/`: downloaded media, extracted audio, transcripts.
  - `notes/`: rendered Markdown notes and analysis output.
- `tests/`: unit tests and fixture-backed parser/render/analyzer coverage.

## Boundaries

- Network access is only allowed in source-specific fetch scripts: `scripts/fetch_xhs.py` and `scripts/fetch_wechat.py`.
- Rendering logic belongs only in `scripts/render_note.py`.
- Transcription logic belongs only in `scripts/transcribe_audio.py`.
- Keep parser logic separated from I/O whenever possible.
- Prefer pure functions for parsing, normalization, summarization, and path generation.
- Rendering must stay deterministic so tests can assert on output structure.

## Setup

- Create venv: `python -m venv .venv`
- Activate on PowerShell: `.venv\Scripts\Activate.ps1`
- Install deps: `pip install -r requirements.txt`

## Commands

- Fetch one post: `python scripts/fetch_xhs.py --url "https://www.xiaohongshu.com/explore/POST_ID"`
- Fetch one WeChat article: `python scripts/fetch_wechat.py --url "https://mp.weixin.qq.com/s?__biz=...&mid=...&sn=..."`
- Render one note: `python scripts/render_note.py --input data/raw/post.json`
- Batch import: `python scripts/batch_import.py --input-file urls.txt --cookies data/cookies.txt`
- Analyze notes: `python scripts/analyze_notes.py --notes-dir data/notes --output data/notes/_analysis.md`

## Tests

- Run all tests: `python -m pytest`
- Parser and template changes must include tests.
- Changes to parsing should use fixture-backed tests where practical.

## Conventions

- Keep data flow explicit: fetch -> normalize -> optional transcribe -> render -> analyze.
- Save raw artifacts before downstream transformation when practical.
- Avoid hidden side effects in helper functions.
- Keep outputs easy to inspect by hand in Markdown and JSON.

## Secrets

- Secrets, cookies, API keys, and local Obsidian vault paths must never be committed.
- Treat `data/cookies.txt`, local media, and machine-specific output paths as local-only files.
