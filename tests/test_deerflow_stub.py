from workflows.deerflow_adapter import build_deerflow_payload
from workflows.run_deerflow_stub import run_stub


def test_run_stub_returns_completed_tasks():
    payload = {
        "adapter_version": "v1",
        "tasks": [
            {
                "agent_role": "researcher",
                "task_type": "background_research",
                "note_title": "测试笔记",
                "source_url": "https://example.com",
                "priority": 3,
                "instructions": ["Find supporting context."],
                "metadata": {"score": 3},
            }
        ],
    }

    result = run_stub(payload)

    assert result["total_tasks"] == 1
    assert result["completed_tasks"][0]["status"] == "completed"
    assert result["completed_tasks"][0]["agent_role"] == "researcher"
