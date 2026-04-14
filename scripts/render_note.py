from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from local_env import load_local_env


load_local_env()

DEFAULT_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "note.md.j2"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "notes"
DEFAULT_VAULT_SUBDIR = "Inbox/Xiaohongshu"


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "untitled"


def build_environment(template_dir: str | Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["slugify"] = slugify
    return env


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return []
    parts = re.split(r"(?<=[。！？.!?])\s+", cleaned)
    return [part.strip() for part in parts if part.strip()]


def derive_summary(content: str, max_length: int = 180) -> str:
    sentences = split_sentences(content)
    if not sentences:
        return "No summary available."
    summary = sentences[0]
    if len(summary) <= max_length:
        return summary
    shortened = summary[: max_length - 3].rstrip()
    if " " in shortened:
        shortened = shortened.rsplit(" ", 1)[0]
    return shortened + "..."


def derive_key_insights(content: str, limit: int = 3) -> list[str]:
    sentences = split_sentences(content)
    insights: list[str] = []
    for sentence in sentences:
        normalized = normalize_whitespace(sentence)
        if normalized and normalized not in insights:
            insights.append(normalized)
        if len(insights) >= limit:
            break
    return insights


def normalize_transcript(post: dict[str, Any]) -> str | None:
    for key in ("transcript", "audio_transcript", "transcription"):
        value = post.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def format_published_date(value: str) -> str:
    if not value:
        return ""
    return value[:10] if len(value) >= 10 else value


def build_output_filename(post: dict[str, Any]) -> str:
    date_part = format_published_date(post.get("published_at", "")) or "undated"
    title = post.get("title") or post.get("note_id") or "untitled"
    return f"{date_part}-{slugify(title)}.md"


def resolve_notes_output_dir(explicit_output_dir: str | Path | None = None) -> Path:
    if explicit_output_dir:
        return Path(explicit_output_dir)

    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "").strip()
    vault_subdir = os.getenv("OBSIDIAN_IMPORT_SUBDIR", DEFAULT_VAULT_SUBDIR).strip() or DEFAULT_VAULT_SUBDIR
    if vault_path:
        return Path(vault_path) / Path(vault_subdir)

    env_notes_dir = os.getenv("XHS_NOTES_DIR", "").strip()
    if env_notes_dir:
        return Path(env_notes_dir)

    return DEFAULT_OUTPUT_DIR


def prepare_post(post: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(post)
    prepared.setdefault("note_id", prepared.get("post_id", ""))
    prepared.setdefault("title", "")
    prepared.setdefault("url", prepared.get("source_url", ""))
    prepared.setdefault("published_at", prepared.get("publish_time", ""))
    prepared.setdefault("author", {})
    prepared.setdefault("content", "")
    prepared.setdefault("tags", [])
    prepared.setdefault("images", [])
    prepared.setdefault("video_url", "")
    prepared.setdefault("source_type", "xhs")

    if isinstance(prepared.get("author"), str):
        prepared["author"] = {"name": prepared["author"], "user_id": "", "profile_url": ""}

    content = prepared.get("content") or ""
    prepared["summary"] = derive_summary(content)
    prepared["key_insights"] = derive_key_insights(content)
    prepared["transcript"] = normalize_transcript(prepared)
    prepared["published_date"] = format_published_date(prepared.get("published_at", ""))
    prepared["safe_filename"] = build_output_filename(prepared)
    prepared["obsidian_title"] = prepared.get("title") or prepared.get("note_id") or "Untitled"
    return prepared


def render_markdown(post: dict[str, Any], template_path: str | Path = DEFAULT_TEMPLATE) -> str:
    template_file = Path(template_path)
    env = build_environment(template_file.parent)
    template = env.get_template(template_file.name)
    return template.render(post=prepare_post(post)).strip() + "\n"


def choose_output_path(post: dict[str, Any], output_dir: str | Path | None = None) -> Path:
    prepared = prepare_post(post)
    path = resolve_notes_output_dir(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path / prepared["safe_filename"]


def render_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    output_dir: str | Path | None = None,
    template_path: str | Path = DEFAULT_TEMPLATE,
) -> Path:
    input_file = Path(input_path)
    data = json.loads(input_file.read_text(encoding="utf-8"))
    destination = Path(output_path) if output_path else choose_output_path(data, output_dir=output_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_markdown(data, template_path=template_path), encoding="utf-8")
    return destination


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render an Obsidian Markdown note from normalized JSON.")
    parser.add_argument("--input", required=True, help="Normalized post JSON path")
    parser.add_argument("--output", help="Optional explicit Markdown output path")
    parser.add_argument("--output-dir", help="Directory for rendered Markdown notes when --output is not set")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="Optional Jinja template path")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    output = render_file(
        args.input,
        args.output,
        output_dir=args.output_dir,
        template_path=args.template,
    )
    print(json.dumps({"output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
