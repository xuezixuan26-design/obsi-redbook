from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_COMMAND_TEMPLATE = "deerflow run --input {input} --output {output}"


def load_payload(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_runtime_request(task: dict[str, Any], index: int) -> dict[str, Any]:
    slug = f"{index:02d}-{task.get('task_type', 'task')}"
    return {
        "request_version": "v1",
        "task_id": slug,
        "agent_role": task.get("agent_role", "generalist"),
        "task_type": task.get("task_type", "unknown"),
        "note_title": task.get("note_title", "Untitled note"),
        "source_url": task.get("source_url", ""),
        "priority": task.get("priority", 0),
        "instructions": task.get("instructions", []),
        "metadata": task.get("metadata", {}),
    }


def materialize_runtime_requests(payload: dict[str, Any], output_dir: str | Path) -> list[Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    request_paths: list[Path] = []

    for index, task in enumerate(payload.get("tasks", []), start=1):
        request = build_runtime_request(task, index)
        request_path = directory / f"{request['task_id']}.json"
        request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
        request_paths.append(request_path)

    return request_paths


def build_command(template: str, input_path: Path, output_path: Path) -> list[str]:
    command = template.format(input=str(input_path), output=str(output_path))
    return shlex.split(command, posix=False)


def execute_runtime_requests(
    request_paths: list[Path],
    results_dir: str | Path,
    command_template: str,
    dry_run: bool = True,
) -> list[dict[str, Any]]:
    output_root = Path(results_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for request_path in request_paths:
        result_path = output_root / request_path.name
        command = build_command(command_template, request_path, result_path)
        if dry_run:
            results.append(
                {
                    "request": str(request_path),
                    "result": str(result_path),
                    "status": "planned",
                    "command": command,
                }
            )
            continue

        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        results.append(
            {
                "request": str(request_path),
                "result": str(result_path),
                "status": "completed" if completed.returncode == 0 else "failed",
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )

    return results


def write_json(payload: Any, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def render_runtime_report(summary: dict[str, Any]) -> str:
    lines = [
        "# DeerFlow Runtime Adapter",
        "",
        f"- Dry run: {summary.get('dry_run')}",
        f"- Requests materialized: {summary.get('request_count')}",
        f"- Command template: {summary.get('command_template')}",
        "",
        "## Requests",
        "",
    ]

    for item in summary.get("executions", []):
        lines.append(f"### {Path(item['request']).name}")
        lines.append(f"- Status: {item['status']}")
        lines.append(f"- Request: {item['request']}")
        lines.append(f"- Result: {item['result']}")
        lines.append(f"- Command: {' '.join(item['command'])}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_text(content: str, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare or execute DeerFlow runtime request bundles from a task payload.")
    parser.add_argument("--payload", required=True, help="Path to DeerFlow payload JSON")
    parser.add_argument("--requests-dir", default="data/analysis/deerflow-requests", help="Directory for per-task request bundles")
    parser.add_argument("--results-dir", default="data/analysis/deerflow-results", help="Directory for runtime result files")
    parser.add_argument("--output", default="data/analysis/deerflow-runtime-run.json", help="Summary JSON output")
    parser.add_argument("--report-output", help="Optional Markdown report path")
    parser.add_argument("--command-template", help="Override runtime command template")
    parser.add_argument("--execute", action="store_true", help="Actually run the configured command for each request")
    args = parser.parse_args()

    payload = load_payload(args.payload)
    request_paths = materialize_runtime_requests(payload, args.requests_dir)
    command_template = args.command_template or os.getenv("DEERFLOW_COMMAND_TEMPLATE", DEFAULT_COMMAND_TEMPLATE)
    executions = execute_runtime_requests(
        request_paths=request_paths,
        results_dir=args.results_dir,
        command_template=command_template,
        dry_run=not args.execute,
    )
    summary = {
        "adapter": "deerflow-runtime",
        "dry_run": not args.execute,
        "command_template": command_template,
        "request_count": len(request_paths),
        "executions": executions,
    }
    print(write_json(summary, args.output))

    if args.report_output:
        print(write_text(render_runtime_report(summary), args.report_output))


if __name__ == "__main__":
    main()
