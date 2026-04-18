import shutil
from pathlib import Path

from workflows.apply_deerflow_results import apply_results


def test_apply_results_creates_enriched_note_copy():
    sandbox = Path(__file__).resolve().parents[1] / "data" / "apply_test_tmp"
    notes_dir = sandbox / "notes"
    enriched_dir = sandbox / "enriched"
    if sandbox.exists():
        shutil.rmtree(sandbox)
    notes_dir.mkdir(parents=True)

    try:
        note_path = notes_dir / "note.md"
        note_path.write_text(
            """---
title: "测试笔记"
---

# 测试笔记

原始内容。
""",
            encoding="utf-8",
        )

        run_result = {
            "completed_tasks": [
                {
                    "note_title": "测试笔记",
                    "task_type": "background_research",
                    "agent_role": "researcher",
                    "status": "completed",
                    "result_summary": "Prepared a background research brief.",
                }
            ]
        }

        summary = apply_results(run_result, notes_dir, enriched_dir)

        assert summary["notes_enriched"] == 1
        enriched_note = enriched_dir / "note.md"
        assert enriched_note.exists()
        assert "## DeerFlow Enhancements" in enriched_note.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
