from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .fetch_xhs import NotePayload, fetch_html, parse_note_from_html, save_payload
    from .render_note import default_output_path, render_markdown, write_markdown
except ImportError:
    from fetch_xhs import NotePayload, fetch_html, parse_note_from_html, save_payload
    from render_note import default_output_path, render_markdown, write_markdown


def import_html_file(html_path: str | Path, raw_dir: str | Path, notes_dir: str | Path, template: str | Path) -> tuple[Path, Path]:
    html_file = Path(html_path)
    payload: NotePayload = parse_note_from_html(html_file.read_text(encoding="utf-8"), source_url=str(html_file))
    raw_output = Path(raw_dir) / f"{payload.note_id}.json"
    note_output = Path(notes_dir) / default_output_path(payload, notes_dir="").name
    save_payload(payload, raw_output)
    markdown = render_markdown(payload, template)
    write_markdown(markdown, note_output)
    return raw_output, note_output


def import_live_url(url: str, cookies: str | None, raw_dir: str | Path, notes_dir: str | Path, template: str | Path) -> tuple[Path, Path]:
    html = fetch_html(url, cookies_file=cookies)
    payload = parse_note_from_html(html, source_url=url)
    raw_output = Path(raw_dir) / f"{payload.note_id}.json"
    note_output = Path(notes_dir) / default_output_path(payload, notes_dir="").name
    save_payload(payload, raw_output)
    markdown = render_markdown(payload, template)
    write_markdown(markdown, note_output)
    return raw_output, note_output


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch import Xiaohongshu notes from HTML exports or live URLs.")
    parser.add_argument("--html", nargs="*", default=[], help="One or more saved HTML files")
    parser.add_argument("--url", nargs="*", default=[], help="One or more live note URLs")
    parser.add_argument("--cookies", help="Cookies file for live fetch")
    parser.add_argument("--raw-dir", default="data/raw", help="Directory for normalized JSON")
    parser.add_argument("--notes-dir", default="data/notes", help="Directory for rendered Markdown")
    parser.add_argument("--template", default="templates/note.md.j2", help="Jinja2 note template")
    args = parser.parse_args()

    results: list[tuple[Path, Path]] = []
    for html_path in args.html:
        results.append(import_html_file(html_path, args.raw_dir, args.notes_dir, args.template))
    for url in args.url:
        results.append(import_live_url(url, args.cookies, args.raw_dir, args.notes_dir, args.template))

    for raw_output, note_output in results:
        print(f"raw={raw_output} note={note_output}")


if __name__ == "__main__":
    main()
