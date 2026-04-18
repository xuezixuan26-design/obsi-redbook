from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import requests


STATE_SCRIPT_PATTERNS = (
    r"<script[^>]*id=[\"']__INITIAL_STATE__[\"'][^>]*>(.*?)</script>",
    r"<script[^>]*>\\s*window\\.__INITIAL_STATE__\\s*=\\s*(\\{.*?\\})\\s*;</script>",
    r"<script[^>]*id=[\"']__NEXT_DATA__[\"'][^>]*>(.*?)</script>",
    r"<script[^>]*>\\s*window\\.__REDUX_STATE__\\s*=\\s*(\\{.*?\\})\\s*;</script>",
)


@dataclass(slots=True)
class NotePayload:
    note_id: str
    source_url: str = ""
    title: str = ""
    author: str = ""
    author_id: str = ""
    publish_time: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    video_urls: list[str] = field(default_factory=list)
    audio_urls: list[str] = field(default_factory=list)
    transcript: str = ""
    raw_state_keys: list[str] = field(default_factory=list)


def load_cookies_from_netscape(path: str | Path) -> requests.cookies.RequestsCookieJar:
    jar = requests.cookies.RequestsCookieJar()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split("\t")
        if len(parts) < 7:
            continue
        domain, _, cookie_path, secure_flag, _, name, value = parts[:7]
        jar.set(name, value, domain=domain, path=cookie_path, secure=secure_flag.upper() == "TRUE")
    return jar


def fetch_html(url: str, cookies_file: str | Path | None = None, user_agent: str | None = None, timeout: int = 20) -> str:
    headers = {
        "User-Agent": user_agent
        or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    cookies = load_cookies_from_netscape(cookies_file) if cookies_file else None
    response = requests.get(url, headers=headers, cookies=cookies, timeout=timeout)
    response.raise_for_status()
    return response.text


def extract_embedded_state(html: str) -> dict[str, Any]:
    for pattern in STATE_SCRIPT_PATTERNS:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if not match:
            continue
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return json.loads(candidate.rstrip(";"))
    raise ValueError("Could not locate embedded state in the provided HTML.")


def _coalesce(data: dict[str, Any], *paths: tuple[str, ...], default: Any = "") -> Any:
    for path in paths:
        current: Any = data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        if current not in (None, ""):
            return current
    return default


def _extract_first_note_container(state: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        _coalesce(state, ("note",)),
        _coalesce(state, ("noteData",)),
        _coalesce(state, ("props", "pageProps", "note")),
        _coalesce(state, ("props", "pageProps", "initialState", "note")),
        _coalesce(state, ("currentNote",)),
        _coalesce(state, ("data", "note")),
    ]
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate:
            return candidate

    stack: list[Any] = [state]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            if {"noteId", "title"}.issubset(item.keys()) or {"id", "desc"}.issubset(item.keys()):
                return item
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)

    raise ValueError("Could not find a note-like object in the embedded state.")


def normalize_note_payload(state: dict[str, Any], source_url: str = "") -> NotePayload:
    note = _extract_first_note_container(state)
    note_id = str(_coalesce(note, ("noteId",), ("id",), default="unknown-note"))
    tags = _coalesce(note, ("tags",), ("tagList",), default=[])

    normalized_tags: list[str] = []
    for tag in tags or []:
        if isinstance(tag, str):
            normalized_tags.append(tag.lstrip("#"))
        elif isinstance(tag, dict):
            normalized_tags.append(str(tag.get("name", "")).lstrip("#"))

    image_list = _coalesce(note, ("images",), ("imageList",), default=[])
    images: list[str] = []
    for image in image_list or []:
        if isinstance(image, str):
            images.append(image)
        elif isinstance(image, dict):
            images.append(str(image.get("url") or image.get("src") or image.get("link") or image.get("urlDefault", "")))

    media = _coalesce(note, ("media",), default={})
    video_urls: list[str] = []
    audio_urls: list[str] = []
    if isinstance(media, dict):
        maybe_video = media.get("video") or media.get("videos") or []
        maybe_audio = media.get("audio") or media.get("audios") or []
        for item in maybe_video if isinstance(maybe_video, list) else [maybe_video]:
            if isinstance(item, str):
                video_urls.append(item)
            elif isinstance(item, dict):
                video_urls.append(str(item.get("url") or item.get("masterUrl") or ""))
        for item in maybe_audio if isinstance(maybe_audio, list) else [maybe_audio]:
            if isinstance(item, str):
                audio_urls.append(item)
            elif isinstance(item, dict):
                audio_urls.append(str(item.get("url") or item.get("streamUrl") or ""))

    author = _coalesce(note, ("author", "name"), ("user", "nickname"), ("nickname",), default="")
    author_id = str(_coalesce(note, ("author", "userId"), ("user", "userId"), ("userId",), default=""))
    publish_time = str(_coalesce(note, ("publishTime",), ("time",), ("lastUpdateTime",), default=""))
    content = str(_coalesce(note, ("content",), ("desc",), ("description",), default="")).strip()
    title = str(_coalesce(note, ("title",), default="")).strip() or f"Rednote {note_id}"

    return NotePayload(
        note_id=note_id,
        source_url=source_url,
        title=title,
        author=str(author).strip(),
        author_id=author_id,
        publish_time=publish_time,
        content=content,
        tags=[tag for tag in normalized_tags if tag],
        images=[image for image in images if image],
        video_urls=[url for url in video_urls if url],
        audio_urls=[url for url in audio_urls if url],
        raw_state_keys=sorted(state.keys()),
    )


def parse_note_from_html(html: str, source_url: str = "") -> NotePayload:
    state = extract_embedded_state(html)
    return normalize_note_payload(state, source_url=source_url)


def save_payload(payload: NotePayload, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and normalize a Xiaohongshu note.")
    parser.add_argument("--url", required=True, help="Xiaohongshu note URL")
    parser.add_argument("--cookies", help="Path to exported Netscape cookies file")
    parser.add_argument("--output", help="Path to save normalized JSON payload")
    parser.add_argument("--save-html", help="Path to save raw HTML response")
    parser.add_argument("--user-agent", help="Optional custom User-Agent header")
    args = parser.parse_args()

    html = fetch_html(args.url, cookies_file=args.cookies, user_agent=args.user_agent)
    if args.save_html:
        save_html_path = Path(args.save_html)
        save_html_path.parent.mkdir(parents=True, exist_ok=True)
        save_html_path.write_text(html, encoding="utf-8")

    payload = parse_note_from_html(html, source_url=args.url)
    output = args.output or Path("data/raw") / f"{payload.note_id}.json"
    print(save_payload(payload, output))


if __name__ == "__main__":
    main()
