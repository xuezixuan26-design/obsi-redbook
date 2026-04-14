from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from fetch_wechat import FetchError as WeChatFetchError
from fetch_wechat import ParseError as WeChatParseError
from fetch_wechat import fetch_article
from fetch_xhs import FetchError as XhsFetchError
from fetch_xhs import ParseError as XhsParseError
from fetch_xhs import fetch_post
from local_env import load_local_env
from render_note import render_file, resolve_notes_output_dir
from transcribe_audio import LocalPlaceholderBackend, TranscriptionError, transcribe_media


load_local_env()

DEFAULT_COOKIES_PATH = Path("data/cookies.txt")
DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_MEDIA_DIR = Path("data/media")
DEFAULT_NOTES_DIR = resolve_notes_output_dir()


@dataclass(slots=True)
class ImportItemResult:
    url: str
    status: str
    source_type: str | None = None
    note_id: str | None = None
    raw_json_path: str | None = None
    note_path: str | None = None
    transcript_path: str | None = None
    error: str | None = None


def parse_url_lines(text: str) -> list[str]:
    urls: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def load_urls(input_file: str | Path) -> list[str]:
    return parse_url_lines(Path(input_file).read_text(encoding="utf-8"))


def detect_source_type(url: str) -> str:
    hostname = urlparse(url).netloc.lower()
    if "xiaohongshu.com" in hostname or "xhslink.com" in hostname or "rednote" in hostname:
        return "xhs"
    if "mp.weixin.qq.com" in hostname:
        return "wechat"
    raise ValueError(f"Unsupported URL source: {url}")


def update_raw_json(raw_json_path: str | Path, data: dict) -> Path:
    path = Path(raw_json_path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def maybe_transcribe_video(
    normalized: dict,
    *,
    enable_transcription: bool,
    media_dir: str | Path,
    backend_name: str,
    ffmpeg_bin: str,
    language: str | None,
    transcribe_func: Callable[..., object] = transcribe_media,
) -> tuple[dict, str | None]:
    if not enable_transcription:
        return normalized, None
    video_url = normalized.get("video_url")
    if not video_url:
        return normalized, None

    result = transcribe_func(
        video_url,
        backend_name=backend_name,
        media_dir=media_dir,
        ffmpeg_bin=ffmpeg_bin,
        language=language,
    )
    normalized = dict(normalized)
    normalized["transcript"] = result.transcript_text
    normalized["transcript_path"] = result.transcript_path.as_posix()
    normalized["transcript_backend"] = result.backend
    return normalized, result.transcript_path.as_posix()


def default_fetch_dispatcher(
    source_type: str,
    url: str,
    *,
    cookies_path: str | Path,
    raw_dir: str | Path,
) -> object:
    if source_type == "xhs":
        return fetch_post(url, cookies_path=cookies_path, raw_dir=raw_dir)
    if source_type == "wechat":
        return fetch_article(url, raw_dir=raw_dir)
    raise ValueError(f"Unsupported source type: {source_type}")


def process_url(
    url: str,
    *,
    cookies_path: str | Path,
    raw_dir: str | Path,
    media_dir: str | Path,
    notes_dir: str | Path,
    template_path: str | Path | None,
    enable_transcription: bool,
    transcription_backend: str,
    ffmpeg_bin: str,
    language: str | None,
    fetch_dispatcher: Callable[..., object] = default_fetch_dispatcher,
    transcribe_func: Callable[..., object] = transcribe_media,
    render_func: Callable[..., Path] = render_file,
) -> ImportItemResult:
    try:
        source_type = detect_source_type(url)
        fetch_result = fetch_dispatcher(
            source_type,
            url,
            cookies_path=cookies_path,
            raw_dir=raw_dir,
        )
        normalized = dict(fetch_result.normalized)
        normalized.setdefault("source_type", source_type)
        normalized, transcript_path = maybe_transcribe_video(
            normalized,
            enable_transcription=enable_transcription,
            media_dir=media_dir,
            backend_name=transcription_backend,
            ffmpeg_bin=ffmpeg_bin,
            language=language,
            transcribe_func=transcribe_func,
        )
        update_raw_json(fetch_result.raw_state_path, normalized)
        note_path = render_func(
            fetch_result.raw_state_path,
            output_dir=notes_dir,
            template_path=template_path,
        )
        return ImportItemResult(
            url=url,
            status="succeeded",
            source_type=source_type,
            note_id=normalized.get("note_id"),
            raw_json_path=Path(fetch_result.raw_state_path).as_posix(),
            note_path=Path(note_path).as_posix(),
            transcript_path=transcript_path,
        )
    except (
        XhsFetchError,
        XhsParseError,
        WeChatFetchError,
        WeChatParseError,
        TranscriptionError,
        OSError,
        ValueError,
    ) as exc:
        return ImportItemResult(url=url, status="failed", error=str(exc))


def summarize_results(results: list[ImportItemResult]) -> dict:
    succeeded = [item for item in results if item.status == "succeeded"]
    failed = [item for item in results if item.status == "failed"]
    return {
        "total_urls": len(results),
        "succeeded": len(succeeded),
        "failed": len(failed),
        "output_note_paths": [item.note_path for item in succeeded if item.note_path],
        "results": [
            {
                "url": item.url,
                "status": item.status,
                "source_type": item.source_type,
                "note_id": item.note_id,
                "raw_json_path": item.raw_json_path,
                "note_path": item.note_path,
                "transcript_path": item.transcript_path,
                "error": item.error,
            }
            for item in results
        ],
    }


def batch_import(
    urls: list[str],
    *,
    cookies_path: str | Path = DEFAULT_COOKIES_PATH,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    media_dir: str | Path = DEFAULT_MEDIA_DIR,
    notes_dir: str | Path = DEFAULT_NOTES_DIR,
    template_path: str | Path | None = None,
    enable_transcription: bool = False,
    transcription_backend: str = LocalPlaceholderBackend.name,
    ffmpeg_bin: str = "ffmpeg",
    language: str | None = None,
    fetch_dispatcher: Callable[..., object] = default_fetch_dispatcher,
    transcribe_func: Callable[..., object] = transcribe_media,
    render_func: Callable[..., Path] = render_file,
) -> dict:
    resolved_notes_dir = resolve_notes_output_dir(notes_dir)
    Path(raw_dir).mkdir(parents=True, exist_ok=True)
    Path(media_dir).mkdir(parents=True, exist_ok=True)
    resolved_notes_dir.mkdir(parents=True, exist_ok=True)

    results: list[ImportItemResult] = []
    for url in urls:
        results.append(
            process_url(
                url,
                cookies_path=cookies_path,
                raw_dir=raw_dir,
                media_dir=media_dir,
                notes_dir=resolved_notes_dir,
                template_path=template_path,
                enable_transcription=enable_transcription,
                transcription_backend=transcription_backend,
                ffmpeg_bin=ffmpeg_bin,
                language=language,
                fetch_dispatcher=fetch_dispatcher,
                transcribe_func=transcribe_func,
                render_func=render_func,
            )
        )
    return summarize_results(results)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch import Xiaohongshu or WeChat URLs into Markdown notes.")
    parser.add_argument("--input-file", required=True, help="Text file with one URL per line")
    parser.add_argument("--cookies", default=str(DEFAULT_COOKIES_PATH), help="Path to exported Xiaohongshu cookies")
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR), help="Directory for normalized JSON")
    parser.add_argument("--media-dir", default=str(DEFAULT_MEDIA_DIR), help="Directory for media and transcripts")
    parser.add_argument("--notes-dir", help="Directory for rendered Markdown notes")
    parser.add_argument("--template", help="Optional note template path")
    parser.add_argument(
        "--transcribe-video",
        action="store_true",
        help="When a fetched item contains video, run the transcription pipeline",
    )
    parser.add_argument(
        "--transcription-backend",
        default=LocalPlaceholderBackend.name,
        help="Transcription backend name",
    )
    parser.add_argument("--ffmpeg-bin", default="ffmpeg", help="ffmpeg binary name or path")
    parser.add_argument("--language", help="Optional language hint for transcription")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    urls = load_urls(args.input_file)
    summary = batch_import(
        urls,
        cookies_path=args.cookies,
        raw_dir=args.raw_dir,
        media_dir=args.media_dir,
        notes_dir=args.notes_dir,
        template_path=args.template,
        enable_transcription=args.transcribe_video,
        transcription_backend=args.transcription_backend,
        ffmpeg_bin=args.ffmpeg_bin,
        language=args.language,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
