from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader


WORD_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}")
MEDIA_HINTS = ("视频", "音频", "播客", "口播", "voice", "audio", "video", "transcript")
RESEARCH_HINTS = ("品牌", "市场", "趋势", "竞品", "开店", "行业", "strategy", "trend", "research")
DEEP_DIVE_HINTS = ("总结", "复盘", "选题", "洞察", "方法", "经验", "分析", "framework")


@dataclass(slots=True)
class ParsedNote:
    path: Path
    title: str
    tags: list[str]
    content: str
    source_url: str


def parse_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    if not markdown.startswith("---\n"):
        return {}, markdown
    parts = markdown.split("---\n", 2)
    if len(parts) < 3:
        return {}, markdown

    raw_frontmatter = parts[1]
    body = parts[2].strip()
    data: dict[str, Any] = {}
    current_key = ""

    for line in raw_frontmatter.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key:
            data.setdefault(current_key, []).append(line[4:].strip().strip("\"'"))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        value = value.strip()
        data[current_key] = [] if value == "" else value.strip("\"'")

    return data, body


def load_note(path: str | Path) -> ParsedNote:
    markdown = Path(path).read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(markdown)
    tags = frontmatter.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    return ParsedNote(
        path=Path(path),
        title=str(frontmatter.get("title", Path(path).stem)),
        tags=list(tags),
        content=body,
        source_url=str(frontmatter.get("source_url", "")),
    )


def summarize_text(text: str, sentence_count: int = 2) -> str:
    pieces = re.split(r"(?<=[。！？.!?])\s+|\n+", text.strip())
    selected = [piece.strip() for piece in pieces if piece.strip()][:sentence_count]
    return " ".join(selected)


def extract_keywords(text: str, limit: int = 8) -> list[str]:
    counter = Counter(WORD_PATTERN.findall(text))
    return [token for token, _ in counter.most_common(limit)]


def note_signal_flags(note: ParsedNote) -> dict[str, bool]:
    haystack = f"{note.title}\n{note.content}\n{' '.join(note.tags)}".lower()
    return {
        "has_media_signal": any(flag in haystack for flag in MEDIA_HINTS),
        "needs_background_research": any(flag in haystack for flag in RESEARCH_HINTS),
        "needs_deep_summary": any(flag in haystack for flag in DEEP_DIVE_HINTS),
    }


def cluster_notes(notes: list[ParsedNote]) -> list[dict[str, Any]]:
    clusters: dict[str, list[ParsedNote]] = defaultdict(list)
    for note in notes:
        if note.tags:
            cluster_key = note.tags[0]
        else:
            keywords = extract_keywords(note.content, limit=1)
            cluster_key = keywords[0] if keywords else "uncategorized"
        clusters[cluster_key].append(note)

    results = []
    for cluster_key, members in sorted(clusters.items(), key=lambda item: (-len(item[1]), item[0])):
        combined_text = "\n".join(member.content for member in members)
        results.append(
            {
                "cluster": cluster_key,
                "count": len(members),
                "keywords": extract_keywords(combined_text, limit=6),
                "titles": [member.title for member in members],
            }
        )
    return results


def build_note_actions(note: ParsedNote) -> dict[str, Any]:
    flags = note_signal_flags(note)
    score = 0
    reasons: list[str] = []

    if flags["has_media_signal"]:
        score += 2
        reasons.append("contains media or transcript hints")
    if len(note.content) > 400:
        score += 1
        reasons.append("long-form note")
    if len(note.tags) >= 3:
        score += 1
        reasons.append("rich tag metadata")
    if flags["needs_background_research"]:
        score += 2
        reasons.append("mentions topics that benefit from background research")
    if flags["needs_deep_summary"]:
        score += 1
        reasons.append("contains synthesis-oriented language")

    should_transcribe = flags["has_media_signal"]
    should_enrich = flags["needs_background_research"] or score >= 3
    should_deep_dive = flags["needs_deep_summary"] or score >= 4

    return {
        "title": note.title,
        "source_url": note.source_url,
        "score": score,
        "summary": summarize_text(note.content, sentence_count=1),
        "keywords": extract_keywords(note.content, limit=6),
        "reasons": reasons or ["baseline review"],
        "should_transcribe": should_transcribe,
        "should_enrich": should_enrich,
        "should_deep_dive": should_deep_dive,
        "recommended_actions": [
            action
            for action, enabled in (
                ("transcribe_media", should_transcribe),
                ("background_research", should_enrich),
                ("deep_summary", should_deep_dive),
            )
            if enabled
        ]
        or ["archive_only"],
    }


def build_workflow_plan(note_actions: list[dict[str, Any]], clusters: list[dict[str, Any]]) -> dict[str, Any]:
    queue = sorted(note_actions, key=lambda item: (-item["score"], item["title"]))
    return {
        "workflow_version": "v1",
        "next_best_actions": queue[:5],
        "transcription_queue": [item for item in queue if item["should_transcribe"]],
        "research_queue": [item for item in queue if item["should_enrich"]],
        "deep_dive_queue": [item for item in queue if item["should_deep_dive"]],
        "clusters": clusters,
    }


def analyze_notes(notes_dir: str | Path) -> dict[str, Any]:
    note_paths = sorted(Path(notes_dir).glob("*.md"))
    notes = [load_note(path) for path in note_paths]
    clusters = cluster_notes(notes)
    note_actions = [build_note_actions(note) for note in notes]
    workflow_plan = build_workflow_plan(note_actions, clusters)

    return {
        "note_count": len(notes),
        "clusters": clusters,
        "priorities": sorted(note_actions, key=lambda item: (-item["score"], item["title"])),
        "notes": [
            {
                "title": note.title,
                "tags": note.tags,
                "summary": summarize_text(note.content),
                "keywords": extract_keywords(note.content),
                "source_url": note.source_url,
                **note_signal_flags(note),
            }
            for note in notes
        ],
        "workflow_plan": workflow_plan,
    }


def render_analysis_report(summary: dict[str, Any], template_path: str | Path) -> str:
    template_file = Path(template_path)
    env = Environment(
        loader=FileSystemLoader(str(template_file.parent)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_file.name)
    return template.render(**summary).strip() + "\n"


def write_text(content: str, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def write_json(payload: dict[str, Any], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze imported Obsidian notes for clustering and prioritization.")
    parser.add_argument("--notes-dir", default="data/notes", help="Directory containing rendered Markdown notes")
    parser.add_argument("--output", default="data/analysis/latest-analysis.md", help="Output Markdown report path")
    parser.add_argument("--plan-output", help="Optional JSON output for a DeerFlow-style action plan")
    parser.add_argument("--template", default="templates/analysis.md.j2", help="Analysis report template path")
    args = parser.parse_args()

    summary = analyze_notes(args.notes_dir)
    report_path = write_text(render_analysis_report(summary, args.template), args.output)
    print(report_path)

    if args.plan_output:
        plan_path = write_json(summary["workflow_plan"], args.plan_output)
        print(plan_path)


if __name__ == "__main__":
    main()
