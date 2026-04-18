from pathlib import Path

from scripts.fetch_xhs import NotePayload
from scripts.render_note import render_markdown


def test_render_markdown_includes_frontmatter_and_sections():
    payload = NotePayload(
        note_id="abc123",
        source_url="https://www.xiaohongshu.com/explore/abc123",
        title="上海咖啡地图",
        author="小红薯作者",
        author_id="user-1",
        publish_time="2026-04-18",
        content="这是一篇关于咖啡探店的测试内容。",
        tags=["咖啡", "上海"],
        images=["https://img.example.com/1.jpg"],
        video_urls=[],
        audio_urls=[],
        transcript="",
        raw_state_keys=["note"],
    )
    template_path = Path(__file__).resolve().parents[1] / "templates" / "note.md.j2"

    markdown = render_markdown(payload, template_path)

    assert 'title: "上海咖啡地图"' in markdown
    assert '- "xhs/咖啡"' in markdown
    assert "# 上海咖啡地图" in markdown
    assert "## Images" in markdown
