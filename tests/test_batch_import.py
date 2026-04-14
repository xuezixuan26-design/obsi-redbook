from dataclasses import dataclass
from pathlib import Path
import json
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent / "scripts"))

from batch_import import batch_import, detect_source_type, parse_url_lines, process_url


@dataclass
class DummyFetchResult:
    normalized: dict
    raw_state_path: Path


@dataclass
class DummyTranscriptResult:
    transcript_text: str
    transcript_path: Path
    backend: str


def test_parse_url_lines_ignores_empty_lines_and_comments() -> None:
    text = """
    # comment
    https://www.xiaohongshu.com/explore/a1

    https://mp.weixin.qq.com/s/example
    """
    assert parse_url_lines(text) == [
        "https://www.xiaohongshu.com/explore/a1",
        "https://mp.weixin.qq.com/s/example",
    ]


def test_detect_source_type_handles_xhs_and_wechat() -> None:
    assert detect_source_type("https://www.xiaohongshu.com/explore/a1") == "xhs"
    assert detect_source_type("https://mp.weixin.qq.com/s/example") == "wechat"


def test_process_url_succeeds_for_wechat_without_transcription() -> None:
    workspace = Path(__file__).resolve().parent.parent / "data" / "batch-test-success"
    workspace.mkdir(parents=True, exist_ok=True)
    raw_json = workspace / "wx1.json"
    raw_json.write_text("{}", encoding="utf-8")

    def fake_dispatcher(source_type: str, url: str, **_: object) -> DummyFetchResult:
        assert source_type == "wechat"
        return DummyFetchResult(
            normalized={
                "note_id": "wx1",
                "title": "WeChat Note",
                "content": "Article summary.",
                "url": url,
                "published_at": "2024-06-01T12:00:00+00:00",
                "video_url": None,
                "source_type": "wechat",
            },
            raw_state_path=raw_json,
        )

    def fake_render(input_path: str | Path, **_: object) -> Path:
        note_path = workspace / "2024-06-01-wechat-note.md"
        note_path.write_text(Path(input_path).read_text(encoding="utf-8"), encoding="utf-8")
        return note_path

    result = process_url(
        "https://mp.weixin.qq.com/s/example",
        cookies_path="data/cookies.txt",
        raw_dir=workspace,
        media_dir=workspace,
        notes_dir=workspace,
        template_path=None,
        enable_transcription=False,
        transcription_backend="local-placeholder",
        ffmpeg_bin="ffmpeg",
        language=None,
        fetch_dispatcher=fake_dispatcher,
        render_func=fake_render,
    )

    assert result.status == "succeeded"
    assert result.source_type == "wechat"
    assert result.note_id == "wx1"
    assert result.note_path and result.note_path.endswith("2024-06-01-wechat-note.md")


def test_process_url_adds_transcript_when_video_exists() -> None:
    workspace = Path(__file__).resolve().parent.parent / "data" / "batch-test-transcript"
    workspace.mkdir(parents=True, exist_ok=True)
    raw_json = workspace / "v1.json"
    raw_json.write_text("{}", encoding="utf-8")

    def fake_dispatcher(source_type: str, url: str, **_: object) -> DummyFetchResult:
        assert source_type == "xhs"
        return DummyFetchResult(
            normalized={
                "note_id": "v1",
                "title": "Clip",
                "content": "Short clip.",
                "url": url,
                "published_at": "2024-06-01T12:00:00+00:00",
                "video_url": "https://cdn.example.com/clip.mp4",
                "source_type": "xhs",
            },
            raw_state_path=raw_json,
        )

    def fake_transcribe(source: str, **_: object) -> DummyTranscriptResult:
        return DummyTranscriptResult(
            transcript_text="hello transcript",
            transcript_path=workspace / "clip.transcript.txt",
            backend="local-placeholder",
        )

    def fake_render(input_path: str | Path, **_: object) -> Path:
        note_path = workspace / "2024-06-01-clip.md"
        note_path.write_text(Path(input_path).read_text(encoding="utf-8"), encoding="utf-8")
        return note_path

    result = process_url(
        "https://www.xiaohongshu.com/explore/v1",
        cookies_path="data/cookies.txt",
        raw_dir=workspace,
        media_dir=workspace,
        notes_dir=workspace,
        template_path=None,
        enable_transcription=True,
        transcription_backend="local-placeholder",
        ffmpeg_bin="ffmpeg",
        language="zh",
        fetch_dispatcher=fake_dispatcher,
        transcribe_func=fake_transcribe,
        render_func=fake_render,
    )

    assert result.status == "succeeded"
    assert result.transcript_path and result.transcript_path.endswith("clip.transcript.txt")
    updated = json.loads(raw_json.read_text(encoding="utf-8"))
    assert updated["transcript"] == "hello transcript"
    assert updated["transcript_backend"] == "local-placeholder"


def test_batch_import_collects_partial_failures() -> None:
    workspace = Path(__file__).resolve().parent.parent / "data" / "batch-test-summary"
    workspace.mkdir(parents=True, exist_ok=True)

    def fake_dispatcher(source_type: str, url: str, **_: object) -> DummyFetchResult:
        if url.endswith("/bad"):
            raise ValueError("boom")
        raw_json = workspace / f"{url.rsplit('/', 1)[-1]}.json"
        raw_json.write_text("{}", encoding="utf-8")
        note_id = url.rsplit("/", 1)[-1]
        return DummyFetchResult(
            normalized={
                "note_id": note_id,
                "title": note_id,
                "content": "ok",
                "url": url,
                "published_at": "2024-06-01T12:00:00+00:00",
                "video_url": None,
                "source_type": source_type,
            },
            raw_state_path=raw_json,
        )

    def fake_render(input_path: str | Path, **_: object) -> Path:
        note_path = workspace / (Path(input_path).stem + ".md")
        note_path.write_text("ok", encoding="utf-8")
        return note_path

    summary = batch_import(
        [
            "https://www.xiaohongshu.com/explore/good",
            "https://mp.weixin.qq.com/bad",
        ],
        raw_dir=workspace,
        media_dir=workspace,
        notes_dir=workspace,
        enable_transcription=False,
        fetch_dispatcher=fake_dispatcher,
        render_func=fake_render,
    )

    assert summary["total_urls"] == 2
    assert summary["succeeded"] == 1
    assert summary["failed"] == 1
    assert len(summary["output_note_paths"]) == 1
