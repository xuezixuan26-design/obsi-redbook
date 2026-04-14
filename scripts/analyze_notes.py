from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from local_env import load_local_env


load_local_env()

DEFAULT_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "analysis.md.j2"
DEFAULT_NOTES_DIR = Path(__file__).resolve().parent.parent / "data" / "notes"
DEFAULT_OUTPUT = DEFAULT_NOTES_DIR / "_analysis.md"

SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
METADATA_RE = re.compile(r"^- ([^:]+):\s*(.+?)\s*$", re.MULTILINE)
TAG_RE = re.compile(r"#([A-Za-z0-9_\-\u4e00-\u9fff]+)")
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+\-]{2,}|[\u4e00-\u9fff]{2,}")
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "have",
    "into",
    "about",
    "your",
    "will",
    "best",
    "works",
    "through",
    "early",
    "morning",
    "original",
    "post",
    "source",
    "author",
    "published",
    "summary",
    "content",
    "transcript",
}


def build_environment(template_dir: str | Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def split_sections(markdown: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(markdown))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        sections[match.group(1).strip()] = markdown[start:end].strip()
    return sections


def extract_metadata(markdown: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for key, value in METADATA_RE.findall(markdown):
        normalized_key = key.strip().lower().replace(" ", "_")
        metadata[normalized_key] = value.strip()
    return metadata


def extract_tags(section_text: str) -> list[str]:
    return sorted(set(TAG_RE.findall(section_text)))


def tokenize_text(text: str) -> list[str]:
    tokens: list[str] = []
    for token in TOKEN_RE.findall(text):
        lowered = token.lower()
        if lowered in STOPWORDS:
            continue
        tokens.append(lowered)
    return tokens


def parse_note(note_path: str | Path) -> dict[str, Any]:
    path = Path(note_path)
    markdown = path.read_text(encoding="utf-8")
    lines = markdown.splitlines()
    title = lines[0].removeprefix("# ").strip() if lines else path.stem
    metadata = extract_metadata(markdown)
    sections = split_sections(markdown)
    summary = sections.get("Summary", "")
    key_insights = [
        line.removeprefix("- ").strip()
        for line in sections.get("Key Insights", "").splitlines()
        if line.strip().startswith("- ")
    ]
    tags = extract_tags(sections.get("Tags", ""))
    original_content = sections.get("Original Content", "")
    transcript = sections.get("Transcript", "")
    combined_text = "\n".join(part for part in [summary, original_content, transcript] if part.strip())

    return {
        "path": path.as_posix(),
        "filename": path.name,
        "title": title,
        "metadata": metadata,
        "summary": summary,
        "key_insights": key_insights,
        "tags": tags,
        "original_content": original_content,
        "transcript": transcript,
        "tokens": tokenize_text(combined_text),
    }


def load_notes(notes_dir: str | Path = DEFAULT_NOTES_DIR) -> list[dict[str, Any]]:
    note_files = sorted(Path(notes_dir).glob("*.md"))
    return [parse_note(note_file) for note_file in note_files if note_file.name != "_analysis.md"]


def detect_recurring_themes(notes: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for note in notes:
        counter.update(note["tags"])
    return [{"theme": theme, "count": count} for theme, count in counter.most_common(limit)]


def detect_frequent_topics(notes: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    document_counter: Counter[str] = Counter()
    for note in notes:
        unique_tokens = set(note["tokens"])
        document_counter.update(unique_tokens)
    filtered = [(token, count) for token, count in document_counter.most_common() if count >= 1]
    return [{"topic": token, "note_mentions": count} for token, count in filtered[:limit]]


def detect_research_signals(notes: list[dict[str, Any]], limit: int = 6) -> list[str]:
    signals: list[str] = []
    topics = detect_frequent_topics(notes, limit=20)
    recurring = [item["topic"] for item in topics if item["note_mentions"] >= 2][:3]
    if recurring:
        signals.append("Recurring topics across notes: " + ", ".join(recurring))

    transcript_notes = [note["title"] for note in notes if note["transcript"].strip()]
    if transcript_notes:
        signals.append(
            f"Posts with transcript data may deserve deeper review: {', '.join(transcript_notes[:3])}"
        )

    dense_notes = [note["title"] for note in notes if len(note["key_insights"]) >= 3]
    if dense_notes:
        signals.append(
            f"Insight-dense notes to revisit: {', '.join(dense_notes[:3])}"
        )

    return signals[:limit]


def build_compact_summary(notes: list[dict[str, Any]], themes: list[dict[str, Any]], topics: list[dict[str, Any]]) -> str:
    if not notes:
        return "No notes were available for analysis."
    theme_text = ", ".join(item["theme"] for item in themes[:3]) if themes else "no dominant tags"
    topic_text = ", ".join(item["topic"] for item in topics[:3]) if topics else "no strong repeated topics"
    return (
        f"Reviewed {len(notes)} notes. "
        f"Most visible themes: {theme_text}. "
        f"Frequently repeated topics: {topic_text}."
    )


def analyze_notes(notes_dir: str | Path = DEFAULT_NOTES_DIR) -> dict[str, Any]:
    notes = load_notes(notes_dir)
    themes = detect_recurring_themes(notes)
    topics = detect_frequent_topics(notes)
    signals = detect_research_signals(notes)
    return {
        "note_count": len(notes),
        "compact_summary": build_compact_summary(notes, themes, topics),
        "recurring_themes": themes,
        "frequent_topics": topics,
        "research_signals": signals,
        "notes": [
            {
                "title": note["title"],
                "filename": note["filename"],
                "tags": note["tags"],
                "source": note["metadata"].get("source", ""),
                "published": note["metadata"].get("published", ""),
            }
            for note in notes
        ],
    }


def render_analysis(report: dict[str, Any], template_path: str | Path = DEFAULT_TEMPLATE) -> str:
    template_file = Path(template_path)
    env = build_environment(template_file.parent)
    template = env.get_template(template_file.name)
    return template.render(report=report).strip() + "\n"


def save_analysis(report: dict[str, Any], output_path: str | Path, template_path: str | Path = DEFAULT_TEMPLATE) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_analysis(report, template_path=template_path), encoding="utf-8")
    return destination


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze rendered notes and build a higher-level Markdown summary.")
    parser.add_argument("--notes-dir", default=str(DEFAULT_NOTES_DIR), help="Directory containing Markdown notes")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Markdown analysis output path")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="Analysis template path")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    report = analyze_notes(args.notes_dir)
    output = save_analysis(report, args.output, template_path=args.template)
    print(output.as_posix())


if __name__ == "__main__":
    main()
