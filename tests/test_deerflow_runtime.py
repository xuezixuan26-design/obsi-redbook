import shutil
from pathlib import Path

from workflows.run_deerflow_runtime import execute_runtime_requests, materialize_runtime_requests


def test_materialize_runtime_requests_and_plan_execution():
    sandbox = Path(__file__).resolve().parents[1] / "data" / "runtime_test_tmp"
    if sandbox.exists():
        shutil.rmtree(sandbox)
    requests_dir = sandbox / "requests"
    results_dir = sandbox / "results"

    try:
        payload = {
            "tasks": [
                {
                    "agent_role": "researcher",
                    "task_type": "background_research",
                    "note_title": "测试笔记",
                    "source_url": "https://example.com",
                    "priority": 2,
                    "instructions": ["Find context."],
                    "metadata": {"score": 2},
                }
            ]
        }

        request_paths = materialize_runtime_requests(payload, requests_dir)
        executions = execute_runtime_requests(
            request_paths=request_paths,
            results_dir=results_dir,
            command_template="deerflow run --input {input} --output {output}",
            dry_run=True,
        )

        assert len(request_paths) == 1
        assert request_paths[0].exists()
        assert executions[0]["status"] == "planned"
        assert "deerflow" in executions[0]["command"][0].lower()
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
