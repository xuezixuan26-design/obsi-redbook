import shutil
from pathlib import Path

from scripts.analyze_notes import analyze_notes


def test_analyze_notes_builds_workflow_plan():
    sandbox = Path(__file__).resolve().parents[1] / "data" / "analysis_test_tmp"
    if sandbox.exists():
        shutil.rmtree(sandbox)
    sandbox.mkdir(parents=True)

    note_path = sandbox / "note.md"
    try:
        note_path.write_text(
            """---
title: "品牌复盘笔记"
source_url: "https://example.com/note"
tags:
  - "xhs/咖啡"
  - "xhs/品牌"
  - "xhs/分析"
---

# 品牌复盘笔记

这是一篇关于品牌趋势、选题复盘和音频口播整理的长笔记，后续还需要补背景研究和总结。
""",
            encoding="utf-8",
        )

        result = analyze_notes(sandbox)

        assert result["note_count"] == 1
        assert result["workflow_plan"]["next_best_actions"]
        top_action = result["workflow_plan"]["next_best_actions"][0]
        assert top_action["should_transcribe"] is True
        assert top_action["should_enrich"] is True
        assert top_action["should_deep_dive"] is True
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
