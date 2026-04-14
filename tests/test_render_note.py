from pathlib import Path
import os
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent / "scripts"))

from render_note import build_output_filename, choose_output_path, render_markdown, resolve_notes_output_dir


def sample_post() -> dict:
    return {
        "note_id": "abc123",
        "title": "City Walk",
        "author": {"name": "lin", "user_id": "u1"},
        "content": (
            "A rainy walk through Shanghai. "
            "Stopped for coffee near Fuxing Park. "
            "The route works best early in the morning."
        ),
        "tags": ["travel", "shanghai"],
        "published_at": "2024-06-01T12:00:00+00:00",
        "url": "https://www.xiaohongshu.com/explore/abc123",
    }


def test_render_markdown_contains_expected_sections() -> None:
    rendered = render_markdown(sample_post())
    assert rendered.startswith("# City Walk")
    assert "- Source: [Original Post](https://www.xiaohongshu.com/explore/abc123)" in rendered
    assert "- Published: 2024-06-01" in rendered
    assert "## Summary" in rendered
    assert "A rainy walk through Shanghai." in rendered
    assert "## Key Insights" in rendered
    assert "- Stopped for coffee near Fuxing Park." in rendered
    assert "## Tags" in rendered
    assert "- #travel" in rendered
    assert "## Original Content" in rendered


def test_render_markdown_includes_transcript_when_present() -> None:
    post = sample_post()
    post["transcript"] = "Morning ambience, footsteps, and cafe sounds."
    rendered = render_markdown(post)
    assert "## Transcript" in rendered
    assert "Morning ambience, footsteps, and cafe sounds." in rendered


def test_render_markdown_accepts_wechat_shape() -> None:
    post = {
        "note_id": "wx123",
        "title": "Spring Product Notes",
        "author": {"name": "Growth Lab"},
        "content": "This week we reviewed three skincare products. Hydration repeated often.",
        "tags": [],
        "published_at": "2024-06-01T12:00:00+00:00",
        "url": "https://mp.weixin.qq.com/s?__biz=abc&mid=1&sn=wx123",
        "source_type": "wechat",
    }
    rendered = render_markdown(post)
    assert rendered.startswith("# Spring Product Notes")
    assert "Growth Lab" in rendered
    assert "This week we reviewed three skincare products." in rendered


def test_build_output_filename_is_stable_and_safe() -> None:
    filename = build_output_filename(sample_post())
    assert filename == "2024-06-01-city-walk.md"


def test_choose_output_path_defaults_to_notes_dir() -> None:
    workspace_output = Path(__file__).resolve().parent.parent / "data" / "notes-test"
    output_path = choose_output_path(sample_post(), output_dir=workspace_output)
    assert output_path == workspace_output / "2024-06-01-city-walk.md"


def test_resolve_notes_output_dir_prefers_obsidian_vault_env() -> None:
    previous_vault = os.environ.get("OBSIDIAN_VAULT_PATH")
    previous_subdir = os.environ.get("OBSIDIAN_IMPORT_SUBDIR")
    try:
        os.environ["OBSIDIAN_VAULT_PATH"] = r"C:\Users\Lenovo\Documents\Obsidian Vault"
        os.environ["OBSIDIAN_IMPORT_SUBDIR"] = r"Inbox\Xiaohongshu"
        resolved = resolve_notes_output_dir()
        assert resolved == Path(r"C:\Users\Lenovo\Documents\Obsidian Vault") / Path(r"Inbox\Xiaohongshu")
    finally:
        if previous_vault is None:
            os.environ.pop("OBSIDIAN_VAULT_PATH", None)
        else:
            os.environ["OBSIDIAN_VAULT_PATH"] = previous_vault
        if previous_subdir is None:
            os.environ.pop("OBSIDIAN_IMPORT_SUBDIR", None)
        else:
            os.environ["OBSIDIAN_IMPORT_SUBDIR"] = previous_subdir
