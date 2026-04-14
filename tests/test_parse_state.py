from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent / "scripts"))

from fetch_xhs import (
    FetchError,
    ParseError,
    cookie_jar_from_text,
    normalize_post_payload,
    parse_embedded_state,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_parse_embedded_state_from_initial_state_fixture() -> None:
    html = read_fixture("xhs_initial_state.html")
    state = parse_embedded_state(html)
    assert state["note"]["noteId"] == "abc123"
    assert state["note"]["title"] == "City Walk"


def test_parse_embedded_state_from_next_data_fixture() -> None:
    html = read_fixture("xhs_next_data.html")
    state = parse_embedded_state(html)
    assert state["props"]["pageProps"]["noteData"]["noteId"] == "video999"


def test_normalize_post_payload_extracts_expected_fields() -> None:
    state = parse_embedded_state(read_fixture("xhs_next_data.html"))
    normalized = normalize_post_payload(
        state,
        url="https://www.xiaohongshu.com/explore/video999",
        raw_state_path="data/raw/video999.json",
    )
    assert normalized["url"] == "https://www.xiaohongshu.com/explore/video999"
    assert normalized["note_id"] == "video999"
    assert normalized["author"]["name"] == "lin"
    assert normalized["content"] == "A rainy walk through Shanghai."
    assert normalized["tags"] == ["shanghai", "travel"]
    assert normalized["images"] == ["https://example.com/a.jpg", "https://example.com/b.jpg"]
    assert normalized["video_url"] == "https://example.com/video.mp4"
    assert normalized["raw_state_path"] == "data/raw/video999.json"


def test_cookie_jar_from_raw_cookie_string() -> None:
    jar = cookie_jar_from_text("a=1; web_session=abc123; xsecappid=xhs")
    assert jar.get("web_session") == "abc123"
    assert jar.get("xsecappid") == "xhs"


def test_cookie_jar_from_empty_text_raises() -> None:
    with pytest.raises(FetchError):
        cookie_jar_from_text("   ")


def test_parse_embedded_state_raises_for_missing_payload() -> None:
    with pytest.raises(ParseError):
        parse_embedded_state("<html><body><p>no state here</p></body></html>")
