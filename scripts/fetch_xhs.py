from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from local_env import load_local_env


load_local_env()

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_COOKIES_PATH = Path("data/cookies.txt")
DEFAULT_RAW_DIR = Path("data/raw")

STATE_PATTERNS = (
    re.compile(
        r"<script[^>]*>\s*window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?\s*</script>",
        re.DOTALL,
    ),
    re.compile(
        r"<script[^>]*>\s*window\.__INITIAL_STATE__\s*=\s*JSON\.parse\((?P<quote>[\"'])"
        r"(?P<body>.*?)(?P=quote)\)\s*;?\s*</script>",
        re.DOTALL,
    ),
    re.compile(
        r"<script[^>]*id=[\"']__INITIAL_STATE__[\"'][^>]*>\s*(\{.*?\})\s*</script>",
        re.DOTALL,
    ),
    re.compile(
        r"<script[^>]*>\s*window\.__REDUX_STATE__\s*=\s*(\{.*?\})\s*;?\s*</script>",
        re.DOTALL,
    ),
    re.compile(
        r'<script[^>]*id=[\'"]__NEXT_DATA__[\'"][^>]*>\s*(\{.*?\})\s*</script>',
        re.DOTALL,
    ),
)


class FetchError(RuntimeError):
    """Raised when an HTTP request or file operation needed for fetching fails."""


class ParseError(ValueError):
    """Raised when page state cannot be found or normalized."""


@dataclass(slots=True)
class FetchArtifacts:
    url: str
    note_id: str
    html_path: Path
    raw_state_path: Path
    normalized: dict[str, Any]


def sanitize_filename(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "xhs-post"


def _load_json_blob(blob: str) -> dict[str, Any]:
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as exc:
        raise ParseError("Found embedded state but could not decode JSON.") from exc
    if not isinstance(data, dict):
        raise ParseError("Embedded state decoded successfully but was not a JSON object.")
    return data


def parse_embedded_state(html: str) -> dict[str, Any]:
    """Extract a structured state object from common embedded script patterns."""
    for pattern in STATE_PATTERNS:
        match = pattern.search(html)
        if not match:
            continue
        if "body" in match.groupdict():
            escaped = match.group("body")
            unescaped = bytes(escaped, "utf-8").decode("unicode_escape")
            return _load_json_blob(unescaped)
        return _load_json_blob(match.group(1))
    raise ParseError("No supported embedded page state was found in the HTML.")


def _find_note_object(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        if obj.get("noteId") or (obj.get("id") and any(key in obj for key in ("title", "desc", "content"))):
            return obj
        for value in obj.values():
            found = _find_note_object(value)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_note_object(item)
            if found:
                return found
    return None


def _find_first_list(obj: Any, candidate_keys: tuple[str, ...]) -> list[Any]:
    if isinstance(obj, dict):
        for key in candidate_keys:
            value = obj.get(key)
            if isinstance(value, list):
                return value
        for value in obj.values():
            found = _find_first_list(value, candidate_keys)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_first_list(item, candidate_keys)
            if found:
                return found
    return []


def _pick_text(source: dict[str, Any], keys: tuple[str, ...], default: str = "") -> str:
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            if value.strip():
                return value.strip()
        else:
            return str(value)
    return default


def _normalize_tags(tags_value: Any) -> list[str]:
    tags: list[str] = []
    if not isinstance(tags_value, list):
        return tags
    for tag in tags_value:
        if isinstance(tag, str) and tag.strip():
            tags.append(tag.strip())
        elif isinstance(tag, dict):
            name = _pick_text(tag, ("name", "tagName", "text", "displayName"))
            if name:
                tags.append(name)
    return sorted(set(tags))


def _normalize_images(note: dict[str, Any]) -> list[str]:
    candidates = _find_first_list(note, ("imageList", "images", "imageInfoList"))
    images: list[str] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        url = _pick_text(item, ("url", "imageUrl", "urlDefault", "originUrl", "masterUrl"))
        if url:
            images.append(url)
    return images


def _normalize_video_url(note: dict[str, Any]) -> str | None:
    video_objects: list[dict[str, Any]] = []
    for key in ("video", "videoInfo", "videoMedia", "noteVideoInfo"):
        value = note.get(key)
        if isinstance(value, dict):
            video_objects.append(value)
    nested_media = _find_first_list(note, ("videoList", "videos"))
    video_objects.extend(item for item in nested_media if isinstance(item, dict))

    for item in video_objects:
        url = _pick_text(item, ("masterUrl", "url", "videoUrl", "originUrl"))
        if url:
            return url
    return None


def _coerce_iso_timestamp(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        if value > 10_000_000_000:
            value = value / 1000
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return _coerce_iso_timestamp(int(stripped))
        return stripped or None
    return str(value)


def normalize_post_payload(
    state: dict[str, Any],
    *,
    url: str,
    raw_state_path: str | Path,
) -> dict[str, Any]:
    """Normalize a note-like object from parsed embedded state."""
    note = _find_note_object(state)
    if not note:
        raise ParseError("Could not locate a note-like object in the parsed state.")

    author_value = note.get("user") if isinstance(note.get("user"), dict) else note.get("author")
    author = author_value if isinstance(author_value, dict) else {}
    note_id = _pick_text(note, ("noteId", "id"))
    if not note_id:
        raise ParseError("Parsed note object did not include a note id.")

    normalized = {
        "url": url,
        "note_id": note_id,
        "title": _pick_text(note, ("title", "displayTitle")),
        "author": {
            "name": _pick_text(author, ("nickname", "name"), "Unknown"),
            "user_id": _pick_text(author, ("userId", "id")),
            "profile_url": _pick_text(author, ("profileUrl", "url")),
        },
        "content": _pick_text(note, ("desc", "content", "text")),
        "tags": _normalize_tags(note.get("tagList") or note.get("tags") or note.get("topicList")),
        "images": _normalize_images(note),
        "video_url": _normalize_video_url(note),
        "published_at": _coerce_iso_timestamp(
            note.get("time") or note.get("publishTime") or note.get("publish_time") or note.get("lastUpdateTime")
        ),
        "raw_state_path": Path(raw_state_path).as_posix(),
    }
    return normalized


def cookie_jar_from_text(cookie_text: str) -> requests.cookies.RequestsCookieJar:
    jar = requests.cookies.RequestsCookieJar()
    text = cookie_text.strip()
    if not text:
        raise FetchError("Cookies file was empty.")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    looks_like_netscape = any("\t" in line for line in lines if not line.startswith("#"))
    if looks_like_netscape:
        for line in lines:
            if line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain, _, path_value, secure, _, name, value = parts[:7]
            jar.set(name, value, domain=domain, path=path_value, secure=secure.upper() == "TRUE")
        if not jar:
            raise FetchError("Cookies file looked like Netscape format but no valid cookies were parsed.")
        return jar

    raw_cookie = " ".join(lines)
    for chunk in raw_cookie.split(";"):
        if "=" not in chunk:
            continue
        name, value = chunk.split("=", 1)
        name = name.strip()
        value = value.strip()
        if name:
            jar.set(name, value)
    if not jar:
        raise FetchError("Cookies file did not contain valid cookie pairs.")
    return jar


def load_cookies(cookie_path: str | Path = DEFAULT_COOKIES_PATH) -> requests.cookies.RequestsCookieJar:
    path = Path(cookie_path)
    if not path.exists():
        raise FetchError(f"Cookies file not found: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FetchError(f"Could not read cookies file: {path}") from exc
    return cookie_jar_from_text(text)


def fetch_html(url: str, cookie_jar: requests.cookies.RequestsCookieJar) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.xiaohongshu.com/",
    }
    try:
        response = requests.get(url, headers=headers, cookies=cookie_jar, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FetchError(f"HTTP fetch failed for {url}: {exc}") from exc
    return response.text


def persist_raw_html(html: str, raw_dir: str | Path, note_hint: str) -> Path:
    raw_path = Path(raw_dir)
    raw_path.mkdir(parents=True, exist_ok=True)
    html_path = raw_path / f"{sanitize_filename(note_hint)}.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path


def persist_normalized_json(data: dict[str, Any], raw_dir: str | Path, note_id: str) -> Path:
    raw_path = Path(raw_dir)
    raw_path.mkdir(parents=True, exist_ok=True)
    output_path = raw_path / f"{sanitize_filename(note_id)}.json"
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def download_media(normalized: dict[str, Any], output_dir: str | Path) -> list[str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    urls: list[str] = []
    urls.extend(normalized.get("images", []))
    if normalized.get("video_url"):
        urls.append(normalized["video_url"])

    saved_files: list[str] = []
    for index, media_url in enumerate(urls, start=1):
        parsed = urlparse(media_url)
        suffix = Path(parsed.path).suffix or ".bin"
        destination = output_path / f"media_{index:02d}{suffix}"
        try:
            response = requests.get(media_url, stream=True, timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise FetchError(f"Media download failed for {media_url}: {exc}") from exc
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)
        saved_files.append(str(destination))
    return saved_files


def fetch_post(
    url: str,
    *,
    cookies_path: str | Path = DEFAULT_COOKIES_PATH,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
) -> FetchArtifacts:
    cookie_jar = load_cookies(cookies_path)
    html = fetch_html(url, cookie_jar)
    html_hint = sanitize_filename(Path(urlparse(url).path).name or "xhs-post")
    html_path = persist_raw_html(html, raw_dir, html_hint)

    state = parse_embedded_state(html)
    provisional_note = _find_note_object(state)
    provisional_note_id = _pick_text(provisional_note or {}, ("noteId", "id"), html_hint)
    json_path = Path(raw_dir) / f"{sanitize_filename(provisional_note_id)}.json"
    normalized = normalize_post_payload(state, url=url, raw_state_path=json_path)
    json_path = persist_normalized_json(normalized, raw_dir, normalized["note_id"])
    normalized["raw_state_path"] = json_path.as_posix()
    json_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")

    return FetchArtifacts(
        url=url,
        note_id=normalized["note_id"],
        html_path=html_path,
        raw_state_path=json_path,
        normalized=normalized,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch a Xiaohongshu post and normalize embedded state.")
    parser.add_argument("--url", required=True, help="Xiaohongshu / Rednote post URL")
    parser.add_argument(
        "--cookies",
        default=str(DEFAULT_COOKIES_PATH),
        help="Path to cookies file in Netscape format or raw Cookie header format",
    )
    parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_RAW_DIR),
        help="Directory to store fetched HTML and normalized JSON",
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    try:
        result = fetch_post(args.url, cookies_path=args.cookies, raw_dir=args.raw_dir)
    except (FetchError, ParseError) as exc:
        raise SystemExit(f"Error: {exc}") from exc

    print(
        json.dumps(
            {
                "url": result.url,
                "note_id": result.note_id,
                "html_path": str(result.html_path),
                "raw_state_path": str(result.raw_state_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
