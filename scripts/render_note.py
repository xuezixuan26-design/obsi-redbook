from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

try:
    from .fetch_xhs import NotePayload
except ImportError:
    from fetch_xhs import NotePayload


def slugify(value: str) -> str:
    normalized = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", value.strip().lower(), flags=re.UNICODE)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "note"


def load_payload(path: str | Path) -> NotePayload:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return NotePayload(**data)


def build_note_context(payload: NotePayload) -> dict[str, Any]:
    return {
        "note": asdict(payload),
        "has_media": bool(payload.images or payload.video_urls or payload.audio_urls),
        "obsidian_tags": [f"xhs/{tag}" for tag in payload.tags],
    }


def render_markdown(payload: NotePayload, template_path: str | Path) -> str:
    template_file = Path(template_path)
    env = Environment(loader=FileSystemLoader(str(template_file.parent)), autoescape=False, trim_blocks=True, lstrip_blocks=True)
    template = env.get_template(template_file.name)
    return template.render(**build_note_context(payload)).strip() + "\n"


def write_markdown(markdown: str, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    return output


def default_output_path(payload: NotePayload, notes_dir: str | Path = "data/notes") -> Path:
    filename = f"{payload.note_id}-{slugify(payload.title)}.md"
    return Path(notes_dir) / filename


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a normalized Xiaohongshu note to Markdown.")
    parser.add_argument("--input", required=True, help="Path to normalized note JSON")
    parser.add_argument("--output", help="Output Markdown file path")
    parser.add_argument("--template", default="templates/note.md.j2", help="Jinja2 template path")
    args = parser.parse_args()

    payload = load_payload(args.input)
    markdown = render_markdown(payload, args.template)
    output = Path(args.output) if args.output else default_output_path(payload)
    print(write_markdown(markdown, output))


if __name__ == "__main__":
    main()
