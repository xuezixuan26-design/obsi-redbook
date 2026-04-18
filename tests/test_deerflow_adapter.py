from scripts.analyze_notes import analyze_notes
from workflows.deerflow_adapter import build_deerflow_payload


def test_build_deerflow_payload_exposes_tasks():
    summary = analyze_notes("data/notes")
    payload = build_deerflow_payload(summary["workflow_plan"])

    assert payload["adapter_version"] == "v1"
    assert payload["task_count"] >= 1
    first_task = payload["tasks"][0]
    assert first_task["agent_role"] in {"media-analyst", "researcher", "synthesizer", "archivist"}
    assert first_task["instructions"]
