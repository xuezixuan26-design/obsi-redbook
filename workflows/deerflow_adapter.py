from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class WorkflowTask:
    agent_role: str
    task_type: str
    note_title: str
    source_url: str
    priority: int
    instructions: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_role": self.agent_role,
            "task_type": self.task_type,
            "note_title": self.note_title,
            "source_url": self.source_url,
            "priority": self.priority,
            "instructions": self.instructions,
            "metadata": self.metadata,
        }


def load_plan(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_task_instructions(item: dict[str, Any], task_type: str) -> list[str]:
    summary = item.get("summary", "")
    keywords = item.get("keywords", [])
    reasons = item.get("reasons", [])

    instructions = [
        f"Focus on note: {item.get('title', 'Untitled note')}",
        f"Use the note summary as starting context: {summary}",
    ]
    if keywords:
        instructions.append(f"Prioritize these keywords: {', '.join(keywords)}")
    if reasons:
        instructions.append(f"Why this task was queued: {', '.join(reasons)}")

    if task_type == "transcribe_media":
        instructions.extend(
            [
                "Check whether local media files or sidecar transcripts already exist before creating new artifacts.",
                "If media exists, produce a transcript-ready asset for downstream note enrichment.",
            ]
        )
    elif task_type == "background_research":
        instructions.extend(
            [
                "Look for factual background that strengthens the note without drifting too far from the original topic.",
                "Capture concise references, trends, competitors, or market context relevant to the note.",
            ]
        )
    elif task_type == "deep_summary":
        instructions.extend(
            [
                "Produce a sharper synthesis than the original short summary.",
                "Highlight reusable insights, patterns, and possible follow-up topics for Obsidian.",
            ]
        )
    else:
        instructions.append("Preserve the note in the archive and do not enrich it further.")

    return instructions


def choose_agent_role(task_type: str) -> str:
    mapping = {
        "transcribe_media": "media-analyst",
        "background_research": "researcher",
        "deep_summary": "synthesizer",
        "archive_only": "archivist",
    }
    return mapping.get(task_type, "generalist")


def build_workflow_tasks(plan: dict[str, Any]) -> list[WorkflowTask]:
    tasks: list[WorkflowTask] = []
    seen: set[tuple[str, str]] = set()

    for item in plan.get("next_best_actions", []):
        title = item.get("title", "Untitled note")
        for task_type in item.get("recommended_actions", ["archive_only"]):
            key = (title, task_type)
            if key in seen:
                continue
            seen.add(key)
            tasks.append(
                WorkflowTask(
                    agent_role=choose_agent_role(task_type),
                    task_type=task_type,
                    note_title=title,
                    source_url=item.get("source_url", ""),
                    priority=int(item.get("score", 0)),
                    instructions=build_task_instructions(item, task_type),
                    metadata={
                        "keywords": item.get("keywords", []),
                        "reasons": item.get("reasons", []),
                        "score": item.get("score", 0),
                    },
                )
            )

    return sorted(tasks, key=lambda item: (-item.priority, item.note_title, item.task_type))


def build_deerflow_payload(plan: dict[str, Any]) -> dict[str, Any]:
    tasks = build_workflow_tasks(plan)
    return {
        "adapter_version": "v1",
        "source_workflow_version": plan.get("workflow_version", "unknown"),
        "task_count": len(tasks),
        "clusters": plan.get("clusters", []),
        "tasks": [task.to_dict() for task in tasks],
    }


def render_task_brief(payload: dict[str, Any]) -> str:
    lines = [
        "# DeerFlow Task Brief",
        "",
        f"- Adapter version: {payload.get('adapter_version')}",
        f"- Source workflow version: {payload.get('source_workflow_version')}",
        f"- Tasks queued: {payload.get('task_count')}",
        "",
        "## Tasks",
        "",
    ]

    for task in payload.get("tasks", []):
        lines.append(f"### {task['note_title']} -> {task['task_type']}")
        lines.append(f"- Agent role: {task['agent_role']}")
        lines.append(f"- Priority: {task['priority']}")
        lines.append(f"- Source: {task['source_url'] or 'N/A'}")
        lines.append("- Instructions:")
        for instruction in task["instructions"]:
            lines.append(f"  - {instruction}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_text(content: str, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def write_json(payload: dict[str, Any], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Transform a local workflow plan into a DeerFlow-friendly payload.")
    parser.add_argument("--plan", required=True, help="Path to the JSON plan emitted by scripts/analyze_notes.py")
    parser.add_argument("--output", default="data/analysis/deerflow-payload.json", help="Output JSON payload path")
    parser.add_argument("--brief-output", help="Optional Markdown task brief output")
    args = parser.parse_args()

    plan = load_plan(args.plan)
    payload = build_deerflow_payload(plan)
    print(write_json(payload, args.output))

    if args.brief_output:
        print(write_text(render_task_brief(payload), args.brief_output))


if __name__ == "__main__":
    main()
