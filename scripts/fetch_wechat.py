from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from local_env import load_local_env


load_local_env()

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
DEFAULT_RAW_DIR = Path("data/raw")


class FetchError(RuntimeError):
    """Raised when an HTTP request or file operation needed for fetching fails."""


class ParseError(ValueError):
    """Raised when article content cannot be parsed from the HTML."""


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
    return cleaned.strip("-") or "wechat-article"


def fetch_html(url: str) -> str:
    headers = {"User-Agent": USER_AGENT, "Referer": "https://mp.weixin.qq.com/"}
    try:
        response = requests.get(url, headers=headers, timeout=30)
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


def _match_assignment(pattern: str, html: str) -> str | None:
    match = re.search(pattern, html, re.DOTALL)
    return match.group(1).strip() if match else None


def _decode_js_string(value: str | None) -> str:
    if not value:
        return ""
    return bytes(value, "utf-8").decode("unicode_escape").strip()


def _strip_html(text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def extract_article_fields(html: str, url: str) -> dict[str, Any]:
    title = _decode_js_string(_match_assignment(r"var\s+msg_title\s*=\s*'((?:\\.|[^'])*)';", html))
    author_name = _decode_js_string(_match_assignment(r"var\s+nickname\s*=\s*'((?:\\.|[^'])*)';", html))
    account_name = _decode_js_string(_match_assignment(r"var\s+user_name\s*=\s*'((?:\\.|[^'])*)';", html))
    publish_raw = _match_assignment(r"var\s+publish_time\s*=\s*\"?(\d+)\"?;", html) or _match_assignment(
        r"var\s+ct\s*=\s*\"?(\d+)\"?;",
        html,
    )

    content_match = re.search(
        r"<div[^>]+id=[\"']js_content[\"'][^>]*>(.*?)</div>",
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not content_match:
        raise ParseError("Could not locate WeChat article content in #js_content.")
    content_html = content_match.group(1)
    content = _strip_html(content_html)
    images = re.findall(r"(?:data-src|src)=[\"'](https?://[^\"']+)[\"']", content_html, re.IGNORECASE)
    cleaned_images: list[str] = []
    for image_url in images:
        if image_url not in cleaned_images:
            cleaned_images.append(image_url)

    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    note_id = (
        query.get("sn", [""])[0]
        or query.get("mid", [""])[0]
        or sanitize_filename(title or parsed_url.path or "wechat-article")
    )

    published_at = None
    if publish_raw and publish_raw.isdigit():
        published_at = datetime.fromtimestamp(int(publish_raw), tz=timezone.utc).isoformat()

    return {
        "url": url,
        "note_id": note_id,
        "title": title or note_id,
        "author": {
            "name": author_name or account_name or "Unknown",
            "user_id": account_name,
            "profile_url": "",
        },
        "content": content,
        "tags": [],
        "images": cleaned_images,
        "video_url": None,
        "published_at": published_at,
        "source_type": "wechat",
    }


def fetch_article(url: str, *, raw_dir: str | Path = DEFAULT_RAW_DIR) -> FetchArtifacts:
    html = fetch_html(url)
    parsed_url = urlparse(url)
    html_hint = parsed_url.path.split("/")[-1] or "wechat-article"
    html_path = persist_raw_html(html, raw_dir, html_hint)
    normalized = extract_article_fields(html, url)
    json_path = Path(raw_dir) / f"{sanitize_filename(normalized['note_id'])}.json"
    normalized["raw_state_path"] = json_path.as_posix()
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
    parser = argparse.ArgumentParser(description="Fetch a WeChat public article and normalize it.")
    parser.add_argument("--url", required=True, help="WeChat article URL")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR), help="Directory to store fetched HTML and JSON")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    try:
        result = fetch_article(args.url, raw_dir=args.raw_dir)
    except (FetchError, ParseError) as exc:
        raise SystemExit(f"Error: {exc}") from exc
    print(
        json.dumps(
            {
                "url": result.url,
                "note_id": result.note_id,
                "html_path": result.html_path.as_posix(),
                "raw_state_path": result.raw_state_path.as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
