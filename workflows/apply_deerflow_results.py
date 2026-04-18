from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


TITLE_PATTERN = re.compile(r'^title:\s*"?(.*?)"?$', re.MULTILINE)


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_markdown_notes(notes_dir: str | Path) -> dict[str, dict[str, Any]]:
    notes: dict[str, dict[str, Any]] = {}
    for path in Path(notes_dir).glob("*.md"):
        content = path.read_text(encoding="utf-8")
        title_match = TITLE_PATTERN.search(content)
        title = title_match.group(1) if title_match else path.stem
        notes[title] = {
            "path": path,
            "content": content,
        }
    return notes


def group_results_by_note(run_result: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in run_result.get("completed_tasks", []):
        grouped[item.get("note_title", "Untitled note")].append(item)
    return dict(grouped)


def build_enrichment_record(note_title: str, task_results: list[dict[str, Any]]) -> dict[str, Any]:
    record = {
        "title": note_title,
        "task_count": len(task_results),
        "transcript_update": "",
        "research_update": "",
        "deep_summary_update": "",
        "actions": [],
    }

    for item in task_results:
        task_type = item.get("task_type", "unknown")
        record["actions"].append(
            {
                "task_type": task_type,
                "agent_role": item.get("agent_role", ""),
                "status": item.get("status", ""),
                "result_summary": item.get("result_summary", ""),
            }
        )
        if task_type == "transcribe_media":
            record["transcript_update"] = item.get("result_summary", "")
        elif task_type == "background_research":
            record["research_update"] = item.get("result_summary", "")
        elif task_type == "deep_summary":
            record["deep_summary_update"] = item.get("result_summary", "")

    return record


def render_enhanced_note(original_markdown: str, enrichment: dict[str, Any]) -> str:
    sections = [original_markdown.rstrip(), "", "## DeerFlow Enhancements", ""]
    if enrichment["deep_summary_update"]:
        sections.extend(["### Deep Summary", "", enrichment["deep_summary_update"], ""])
    if enrichment["research_update"]:
        sections.extend(["### Background Research", "", enrichment["research_update"], ""])
    if enrichment["transcript_update"]:
        sections.extend(["### Transcript Status", "", enrichment["transcript_update"], ""])

    sections.extend(["### Applied Tasks", ""])
    for action in enrichment["actions"]:
        sections.append(f"- {action['task_type']}: {action['result_summary']}")

    return "\n".join(sections).rstrip() + "\n"


def write_json(payload: Any, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def write_text(content: str, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def apply_results(
    run_result: dict[str, Any],
    notes_dir: str | Path,
    enriched_notes_dir: str | Path,
) -> dict[str, Any]:
    notes = load_markdown_notes(notes_dir)
    grouped = group_results_by_note(run_result)
    enriched_records: list[dict[str, Any]] = []
    written_notes: list[str] = []

    for note_title, task_results in grouped.items():
        enrichment = build_enrichment_record(note_title, task_results)
        enriched_records.append(enrichment)
        note = notes.get(note_title)
        if not note:
            continue

        target_path = Path(enriched_notes_dir) / note["path"].name
        write_text(render_enhanced_note(note["content"], enrichment), target_path)
        written_notes.append(str(target_path))

    return {
        "enrichment_version": "v1",
        "notes_seen": len(notes),
        "notes_enriched": len(written_notes),
        "written_notes": written_notes,
        "records": enriched_records,
    }


def render_apply_report(summary: dict[str, Any]) -> str:
    lines = [
        "# DeerFlow Result Apply Report",
        "",
        f"- Notes seen: {summary.get('notes_seen')}",
        f"- Notes enriched: {summary.get('notes_enriched')}",
        "",
        "## Enriched Notes",
        "",
    ]

    for path in summary.get("written_notes", []):
        lines.append(f"- {path}")

    lines.extend(["", "## Records", ""])
    for record in summary.get("records", []):
        lines.append(f"### {record['title']}")
        if record["deep_summary_update"]:
            lines.append(f"- Deep summary: {record['deep_summary_update']}")
        if record["research_update"]:
            lines.append(f"- Research: {record['research_update']}")
        if record["transcript_update"]:
            lines.append(f"- Transcript: {record['transcript_update']}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply DeerFlow run results into structured enrichment artifacts.")
    parser.add_argument("--run-result", required=True, help="Path to DeerFlow stub/runtime run JSON")
    parser.add_argument("--notes-dir", default="data/notes", help="Directory containing source Markdown notes")
    parser.add_argument("--enriched-notes-dir", default="data/analysis/enriched-notes", help="Directory for enriched note copies")
    parser.add_argument("--output", default="data/analysis/deerflow-apply-summary.json", help="Summary JSON output")
    parser.add_argument("--report-output", help="Optional Markdown report path")
    args = parser.parse_args()

    summary = apply_results(
        run_result=load_json(args.run_result),
        notes_dir=args.notes_dir,
        enriched_notes_dir=args.enriched_notes_dir,
    )
    print(write_json(summary, args.output))

    if args.report_output:
        print(write_text(render_apply_report(summary), args.report_output))


if __name__ == "__main__":
    main()
