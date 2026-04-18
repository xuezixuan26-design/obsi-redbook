from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


TRANSCRIPT_EXTENSIONS = (".txt", ".srt", ".vtt", ".md")


def extract_audio_with_ffmpeg(media_path: str | Path, audio_output: str | Path, overwrite: bool = True) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg was not found on PATH.")

    media = Path(media_path)
    output = Path(audio_output)
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        ffmpeg,
        "-y" if overwrite else "-n",
        "-i",
        str(media),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output),
    ]
    subprocess.run(command, check=True, capture_output=True)
    return output


def load_sidecar_transcript(media_path: str | Path) -> str:
    media = Path(media_path)
    for extension in TRANSCRIPT_EXTENSIONS:
        candidate = media.with_suffix(extension)
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    return ""


def build_transcription_record(media_path: str | Path, audio_output: str | Path | None = None) -> dict:
    media = Path(media_path)
    transcript = load_sidecar_transcript(media)
    record = {
        "media_path": str(media),
        "audio_output": "",
        "transcript": transcript,
        "transcript_source": "sidecar" if transcript else "none",
    }
    if audio_output:
        record["audio_output"] = str(extract_audio_with_ffmpeg(media, audio_output))
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Optional local audio extraction and transcript loading.")
    parser.add_argument("--media", required=True, help="Path to a media file")
    parser.add_argument("--audio-output", help="Optional output path for extracted WAV audio")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of plain text")
    args = parser.parse_args()

    record = build_transcription_record(args.media, args.audio_output)
    if args.json:
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return

    print(f"media_path={record['media_path']}")
    print(f"audio_output={record['audio_output']}")
    print(f"transcript_source={record['transcript_source']}")
    if record["transcript"]:
        print(record["transcript"])


if __name__ == "__main__":
    main()
