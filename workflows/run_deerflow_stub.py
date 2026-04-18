from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROLE_OUTPUTS = {
    "media-analyst": "Prepared a transcript request and checked for existing sidecar media artifacts.",
    "researcher": "Prepared a background research brief with likely context gaps and reference targets.",
    "synthesizer": "Prepared a deeper synthesis brief with reusable insights and follow-up prompts.",
    "archivist": "Marked the note for archive-only handling with no extra enrichment.",
    "generalist": "Prepared a general review note for follow-up.",
}


def load_payload(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def simulate_task_execution(task: dict[str, Any]) -> dict[str, Any]:
    role = task.get("agent_role", "generalist")
    return {
        "note_title": task.get("note_title", "Untitled note"),
        "task_type": task.get("task_type", "unknown"),
        "agent_role": role,
        "status": "completed",
        "priority": task.get("priority", 0),
        "source_url": task.get("source_url", ""),
        "result_summary": ROLE_OUTPUTS.get(role, ROLE_OUTPUTS["generalist"]),
        "suggested_output_path": f"data/analysis/stub-{task.get('task_type', 'task')}.md",
        "instructions": task.get("instructions", []),
        "metadata": task.get("metadata", {}),
    }


def run_stub(payload: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    completed_tasks: list[dict[str, Any]] = []

    for task in payload.get("tasks", []):
        result = simulate_task_execution(task)
        grouped[result["agent_role"]].append(result)
        completed_tasks.append(result)

    return {
        "stub_version": "v1",
        "source_adapter_version": payload.get("adapter_version", "unknown"),
        "total_tasks": len(completed_tasks),
        "agents_used": sorted(grouped.keys()),
        "grouped_results": dict(grouped),
        "completed_tasks": completed_tasks,
    }


def render_stub_report(run_result: dict[str, Any]) -> str:
    lines = [
        "# DeerFlow Stub Run",
        "",
        f"- Stub version: {run_result.get('stub_version')}",
        f"- Source adapter version: {run_result.get('source_adapter_version')}",
        f"- Total tasks: {run_result.get('total_tasks')}",
        f"- Agents used: {', '.join(run_result.get('agents_used', [])) or 'none'}",
        "",
        "## Completed Tasks",
        "",
    ]

    for task in run_result.get("completed_tasks", []):
        lines.append(f"### {task['note_title']} -> {task['task_type']}")
        lines.append(f"- Agent role: {task['agent_role']}")
        lines.append(f"- Status: {task['status']}")
        lines.append(f"- Priority: {task['priority']}")
        lines.append(f"- Result: {task['result_summary']}")
        lines.append(f"- Suggested output: {task['suggested_output_path']}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_json(payload: dict[str, Any], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def write_text(content: str, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local DeerFlow stub over a DeerFlow-style payload.")
    parser.add_argument("--payload", required=True, help="Path to the DeerFlow payload JSON")
    parser.add_argument("--output", default="data/analysis/deerflow-stub-run.json", help="Output JSON run artifact")
    parser.add_argument("--report-output", help="Optional Markdown run report")
    args = parser.parse_args()

    payload = load_payload(args.payload)
    run_result = run_stub(payload)
    print(write_json(run_result, args.output))

    if args.report_output:
        print(write_text(render_stub_report(run_result), args.report_output))


if __name__ == "__main__":
    main()
