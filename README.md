# xhs-codex-notes

`xhs-codex-notes` is a Codex-native Python repository for importing Xiaohongshu (Rednote) posts into structured Markdown notes for Obsidian. It is designed around exported browser cookies and HTML parsing, with a clean boundary between deterministic ingestion, Markdown rendering, optional transcription helpers, and later-stage analysis that can be upgraded with DeerFlow.

## What It Does

- Fetches or reads Xiaohongshu note pages
- Extracts embedded page state from HTML
- Normalizes note metadata into structured JSON
- Renders Obsidian-friendly Markdown using Jinja2
- Supports batch imports from saved HTML
- Produces lightweight analysis reports for clustering and prioritization

## What It Does Not Do

- No browser automation
- No backend scraping service
- No mandatory cloud transcription dependency

## Requirements

- Python 3.11+
- `requests`
- `jinja2`
- `pytest`
- Optional: `ffmpeg` on `PATH` for audio extraction from media files

## Repository Layout

```text
xhs-codex-notes/
  AGENTS.md
  README.md
  requirements.txt
  .env.example
  scripts/
    __init__.py
    fetch_xhs.py
    transcribe_audio.py
    render_note.py
    batch_import.py
    analyze_notes.py
  templates/
    note.md.j2
    analysis.md.j2
  workflows/
    deerflow_adapter.py
  data/
    raw/
    media/
    notes/
    analysis/
  tests/
    test_parse_state.py
    test_render_note.py
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` if you want reusable paths outside the command line.

## Usage

### Fetch a live note

```powershell
python scripts\fetch_xhs.py --url https://www.xiaohongshu.com/explore/NOTE_ID --cookies cookies.txt --output data\raw\note_payload.json --save-html data\raw\note_page.html
```

### Render Markdown from normalized JSON

```powershell
python scripts\render_note.py --input data\raw\note_payload.json --output data\notes\note.md
```

### Batch import saved HTML

```powershell
python scripts\batch_import.py --html data\raw\sample1.html data\raw\sample2.html --notes-dir data\notes --raw-dir data\raw
```

### Optional transcription helper

```powershell
python scripts\transcribe_audio.py --media data\media\sample.mp4 --audio-output data\media\sample.wav
```

### Analyze imported notes

```powershell
python scripts\analyze_notes.py --notes-dir data\notes --output data\analysis\latest-analysis.md
```

To also emit a structured action plan for a future DeerFlow workflow:

```powershell
python scripts\analyze_notes.py --notes-dir data\notes --output data\analysis\latest-analysis.md --plan-output data\analysis\latest-plan.json
```

To convert that plan into a DeerFlow-style task payload:

```powershell
python workflows\deerflow_adapter.py --plan data\analysis\latest-plan.json --output data\analysis\deerflow-payload.json --brief-output data\analysis\deerflow-brief.md
```

To simulate a local DeerFlow run over that payload:

```powershell
python workflows\run_deerflow_stub.py --payload data\analysis\deerflow-payload.json --output data\analysis\deerflow-stub-run.json --report-output data\analysis\deerflow-stub-report.md
```

To prepare real runtime request bundles without executing anything yet:

```powershell
python workflows\run_deerflow_runtime.py --payload data\analysis\deerflow-payload.json --requests-dir data\analysis\deerflow-requests --results-dir data\analysis\deerflow-results --output data\analysis\deerflow-runtime-run.json --report-output data\analysis\deerflow-runtime-report.md
```

When you are ready to call an external DeerFlow runtime, either pass `--command-template` or set `DEERFLOW_COMMAND_TEMPLATE`, then add `--execute`.

To apply DeerFlow execution results back into reviewable note enrichments:

```powershell
python workflows\apply_deerflow_results.py --run-result data\analysis\deerflow-stub-run.json --notes-dir data\notes --enriched-notes-dir data\analysis\enriched-notes --output data\analysis\deerflow-apply-summary.json --report-output data\analysis\deerflow-apply-report.md
```

## Quick Demo

The repository includes a local sample HTML export at [data/raw/sample_note.html](C:\Users\Lenovo\Desktop\个人网站\xhs-codex-notes\data\raw\sample_note.html). You can run the whole deterministic flow without any live network request:

```powershell
python scripts\batch_import.py --html data\raw\sample_note.html
python scripts\analyze_notes.py --notes-dir data\notes --output data\analysis\sample-analysis.md
```

Expected outputs:

- normalized JSON in `data/raw/sample-001.json`
- rendered Markdown in `data/notes/sample-001-杭州面包店巡礼.md`
- analysis report in `data/analysis/sample-analysis.md`
- optional workflow plan JSON in `data/analysis/sample-plan.json`

## DeerFlow Integration Strategy

Keep DeerFlow above the importer boundary:

- ingestion layer: `fetch_xhs.py`, `transcribe_audio.py`, `render_note.py`, `batch_import.py`
- analysis layer: `analyze_notes.py`

That lets you later add clustering, topic discovery, research enrichment, and prioritization without mixing agent logic into fetch/render code. The current analyzer already emits a DeerFlow-friendly JSON plan containing:

- `next_best_actions`
- `transcription_queue`
- `research_queue`
- `deep_dive_queue`
- cluster summaries

The adapter in `workflows/deerflow_adapter.py` then turns that plan into task objects with:

- `agent_role`
- `task_type`
- `priority`
- `instructions`
- structured metadata for downstream orchestration

## Testing

```powershell
pytest
```
