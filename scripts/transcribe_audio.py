from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from local_env import load_local_env


load_local_env()

DEFAULT_MEDIA_DIR = Path(__file__).resolve().parent.parent / "data" / "media"


class TranscriptionError(RuntimeError):
    """Raised when media preparation or transcription fails."""


@dataclass(slots=True)
class TranscriptResult:
    transcript_path: Path
    metadata_path: Path
    transcript_text: str
    media_path: Path
    audio_path: Path
    backend: str


@dataclass(slots=True)
class BackendResult:
    text: str
    metadata: dict[str, Any]


class TranscriptionBackend(ABC):
    name: str = "base"

    @abstractmethod
    def transcribe(self, audio_path: Path, *, language: str | None = None) -> BackendResult:
        raise NotImplementedError


class LocalPlaceholderBackend(TranscriptionBackend):
    name = "local-placeholder"

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> BackendResult:
        text = (
            "[placeholder transcript]\n"
            f"Audio extracted to: {audio_path.name}\n"
            "Replace LocalPlaceholderBackend with a real local or remote transcription backend."
        )
        metadata = {
            "backend": self.name,
            "language": language,
            "placeholder": True,
        }
        return BackendResult(text=text, metadata=metadata)


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "media"


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def build_media_basename(source: str) -> str:
    if is_url(source):
        parsed = urlparse(source)
        candidate = Path(parsed.path).stem or parsed.netloc
        return slugify(candidate)
    return slugify(Path(source).stem)


def build_ffmpeg_command(media_path: str | Path, audio_path: str | Path, ffmpeg_bin: str = "ffmpeg") -> list[str]:
    return [
        ffmpeg_bin,
        "-y",
        "-i",
        str(media_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(audio_path),
    ]


def ensure_ffmpeg_available(ffmpeg_bin: str = "ffmpeg") -> None:
    if shutil.which(ffmpeg_bin) is None:
        raise TranscriptionError(
            f"ffmpeg binary not found: {ffmpeg_bin}. Install ffmpeg and ensure it is on PATH."
        )


def resolve_backend(name: str) -> TranscriptionBackend:
    if name == LocalPlaceholderBackend.name:
        return LocalPlaceholderBackend()
    raise TranscriptionError(f"Unsupported transcription backend: {name}")


def download_media(source_url: str, output_dir: str | Path = DEFAULT_MEDIA_DIR) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    parsed = urlparse(source_url)
    suffix = Path(parsed.path).suffix or ".mp4"
    destination = output_path / f"{build_media_basename(source_url)}{suffix}"
    try:
        response = requests.get(source_url, stream=True, timeout=60)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise TranscriptionError(f"Failed to download media from {source_url}: {exc}") from exc

    with destination.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                handle.write(chunk)
    return destination


def resolve_media_input(source: str, media_dir: str | Path = DEFAULT_MEDIA_DIR) -> Path:
    if is_url(source):
        return download_media(source, output_dir=media_dir)
    media_path = Path(source)
    if not media_path.exists():
        raise TranscriptionError(f"Local media file not found: {media_path}")
    return media_path


def extract_audio(media_path: str | Path, audio_path: str | Path, ffmpeg_bin: str = "ffmpeg") -> Path:
    ensure_ffmpeg_available(ffmpeg_bin)
    destination = Path(audio_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_command(media_path, destination, ffmpeg_bin=ffmpeg_bin)
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise TranscriptionError(f"ffmpeg failed while extracting audio: {exc.stderr or exc}") from exc
    return destination


def save_transcript_artifacts(
    transcript_text: str,
    *,
    backend_name: str,
    media_path: Path,
    audio_path: Path,
    output_dir: str | Path = DEFAULT_MEDIA_DIR,
    extra_metadata: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    base_name = build_media_basename(audio_path.stem)
    transcript_path = output_path / f"{base_name}.transcript.txt"
    metadata_path = output_path / f"{base_name}.transcript.json"

    transcript_path.write_text(transcript_text, encoding="utf-8")
    metadata = {
        "backend": backend_name,
        "media_path": media_path.as_posix(),
        "audio_path": audio_path.as_posix(),
        "transcript_path": transcript_path.as_posix(),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return transcript_path, metadata_path


def transcribe_media(
    source: str,
    *,
    backend_name: str = LocalPlaceholderBackend.name,
    media_dir: str | Path = DEFAULT_MEDIA_DIR,
    ffmpeg_bin: str = "ffmpeg",
    language: str | None = None,
) -> TranscriptResult:
    media_path = resolve_media_input(source, media_dir=media_dir)
    media_output_dir = Path(media_dir)
    media_output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = media_output_dir / f"{build_media_basename(media_path.name)}.wav"
    audio_path = extract_audio(media_path, audio_path, ffmpeg_bin=ffmpeg_bin)

    backend = resolve_backend(backend_name)
    backend_result = backend.transcribe(audio_path, language=language)
    transcript_path, metadata_path = save_transcript_artifacts(
        backend_result.text,
        backend_name=backend.name,
        media_path=media_path,
        audio_path=audio_path,
        output_dir=media_output_dir,
        extra_metadata=backend_result.metadata,
    )
    return TranscriptResult(
        transcript_path=transcript_path,
        metadata_path=metadata_path,
        transcript_text=backend_result.text,
        media_path=media_path,
        audio_path=audio_path,
        backend=backend.name,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Optional media download, audio extraction, and transcription.")
    parser.add_argument(
        "--source",
        required=True,
        help="Direct video URL or local media file path",
    )
    parser.add_argument(
        "--backend",
        default=LocalPlaceholderBackend.name,
        help="Transcription backend name",
    )
    parser.add_argument(
        "--media-dir",
        default=str(DEFAULT_MEDIA_DIR),
        help="Directory for downloaded media, extracted audio, and transcripts",
    )
    parser.add_argument("--ffmpeg-bin", default="ffmpeg", help="ffmpeg binary name or path")
    parser.add_argument("--language", help="Optional language hint for transcription backends")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    try:
        result = transcribe_media(
            args.source,
            backend_name=args.backend,
            media_dir=args.media_dir,
            ffmpeg_bin=args.ffmpeg_bin,
            language=args.language,
        )
    except TranscriptionError as exc:
        raise SystemExit(f"Error: {exc}") from exc

    print(
        json.dumps(
            {
                "backend": result.backend,
                "media_path": result.media_path.as_posix(),
                "audio_path": result.audio_path.as_posix(),
                "transcript_path": result.transcript_path.as_posix(),
                "metadata_path": result.metadata_path.as_posix(),
                "transcript_text": result.transcript_text,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
