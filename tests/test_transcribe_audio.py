from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent / "scripts"))

from transcribe_audio import (
    LocalPlaceholderBackend,
    TranscriptionError,
    build_ffmpeg_command,
    build_media_basename,
    is_url,
    resolve_backend,
    resolve_media_input,
    save_transcript_artifacts,
)


def test_is_url_detects_http_sources() -> None:
    assert is_url("https://example.com/video.mp4") is True
    assert is_url("C:/media/video.mp4") is False


def test_build_media_basename_is_safe() -> None:
    assert build_media_basename("https://cdn.example.com/My Clip 01.mp4") == "my-clip-01"
    assert build_media_basename("C:/tmp/Walk in Shanghai.mov") == "walk-in-shanghai"


def test_build_ffmpeg_command_has_expected_shape() -> None:
    command = build_ffmpeg_command("input.mp4", "output.wav", ffmpeg_bin="ffmpeg")
    assert command[:4] == ["ffmpeg", "-y", "-i", "input.mp4"]
    assert command[-1] == "output.wav"
    assert "-vn" in command


def test_resolve_backend_returns_placeholder() -> None:
    backend = resolve_backend(LocalPlaceholderBackend.name)
    assert isinstance(backend, LocalPlaceholderBackend)


def test_resolve_media_input_raises_for_missing_local_file() -> None:
    with pytest.raises(TranscriptionError):
        resolve_media_input("C:/does-not-exist/video.mp4")


def test_save_transcript_artifacts_writes_files() -> None:
    tmp_path = Path(__file__).resolve().parent.parent / "data" / "media-test"
    tmp_path.mkdir(parents=True, exist_ok=True)
    media_path = tmp_path / "clip.mp4"
    audio_path = tmp_path / "clip.wav"
    media_path.write_text("video", encoding="utf-8")
    audio_path.write_text("audio", encoding="utf-8")

    transcript_path, metadata_path = save_transcript_artifacts(
        "hello world",
        backend_name="local-placeholder",
        media_path=media_path,
        audio_path=audio_path,
        output_dir=tmp_path,
        extra_metadata={"language": "zh"},
    )

    assert transcript_path.read_text(encoding="utf-8") == "hello world"
    metadata = metadata_path.read_text(encoding="utf-8")
    assert '"backend": "local-placeholder"' in metadata
    assert '"language": "zh"' in metadata
