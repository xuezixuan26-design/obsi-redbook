from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent / "scripts"))

from analyze_notes import analyze_notes, parse_note


def write_note(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_parse_note_extracts_metadata_and_sections() -> None:
    note_path = Path(__file__).resolve().parent.parent / "data" / "analysis-test" / "note-a.md"
    write_note(
        note_path,
        """
# City Walk

- Source: [Original Post](https://www.xiaohongshu.com/explore/a1)
- Author: lin
- Published: 2024-06-01

## Summary

Rainy city walk with cafe stops.

## Key Insights

- Good route for early mornings.
- Cafe stop is a repeat highlight.

## Tags

- #travel
- #shanghai

## Original Content

Rainy city walk with cafe stops and a short route around Fuxing Park.

## Transcript

Ambient street sounds and cafe chatter.
        """,
    )

    parsed = parse_note(note_path)
    assert parsed["title"] == "City Walk"
    assert parsed["metadata"]["author"] == "lin"
    assert parsed["metadata"]["published"] == "2024-06-01"
    assert parsed["tags"] == ["shanghai", "travel"]
    assert parsed["summary"] == "Rainy city walk with cafe stops."
    assert parsed["transcript"] == "Ambient street sounds and cafe chatter."
    assert "shanghai" in parsed["tokens"] or "city" in parsed["tokens"]


def test_analyze_notes_builds_theme_and_topic_summary() -> None:
    notes_dir = Path(__file__).resolve().parent.parent / "data" / "analysis-suite"
    write_note(
        notes_dir / "note-a.md",
        """
# City Walk

- Source: [Original Post](https://www.xiaohongshu.com/explore/a1)
- Author: lin
- Published: 2024-06-01

## Summary

Rainy city walk with cafe stops.

## Key Insights

- Fuxing Park is a strong route anchor.
- Cafe stop is a repeat highlight.
- Morning timing improves the route.

## Tags

- #travel
- #shanghai

## Original Content

Rainy city walk with cafe stops and a short route around Fuxing Park.
        """,
    )
    write_note(
        notes_dir / "note-b.md",
        """
# Beauty Picks

- Source: [Original Post](https://www.xiaohongshu.com/explore/b2)
- Author: mei
- Published: 2024-06-02

## Summary

Skincare picks focused on hydration and sensitive skin.

## Key Insights

- Hydration is the main purchase driver.
- Sensitive skin claims appear repeatedly.

## Tags

- #beauty
- #skincare

## Original Content

Hydration serum, barrier cream, and sensitive skin positioning show up repeatedly.
        """,
    )
    write_note(
        notes_dir / "note-c.md",
        """
# Shanghai Cafe List

- Source: [Original Post](https://www.xiaohongshu.com/explore/c3)
- Author: lin
- Published: 2024-06-03

## Summary

Cafe recommendations around Shanghai parks.

## Key Insights

- Cafe density is highest near major parks.

## Tags

- #travel
- #cafe

## Original Content

Shanghai cafe recommendations near Fuxing Park and nearby streets.

## Transcript

Cafe ambience and walking notes.
        """,
    )

    report = analyze_notes(notes_dir)
    assert report["note_count"] == 3
    assert report["recurring_themes"][0]["theme"] == "travel"
    assert any(item["topic"] == "cafe" for item in report["frequent_topics"])
    assert any("Recurring topics across notes" in signal for signal in report["research_signals"])
    assert "Reviewed 3 notes." in report["compact_summary"]
