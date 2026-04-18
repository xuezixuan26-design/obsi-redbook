from scripts.fetch_xhs import extract_embedded_state, normalize_note_payload, parse_note_from_html


HTML_SAMPLE = """
<html>
  <head></head>
  <body>
    <script id="__INITIAL_STATE__" type="application/json">
      {
        "note": {
          "noteId": "abc123",
          "title": "上海咖啡地图",
          "desc": "周末去了三家新店，顺便录了一段音频感想。",
          "author": {"name": "小红薯作者", "userId": "user-1"},
          "publishTime": "2026-04-18",
          "tags": [{"name": "咖啡"}, {"name": "#上海"}],
          "images": [{"url": "https://img.example.com/1.jpg"}],
          "media": {
            "video": [{"url": "https://video.example.com/1.mp4"}],
            "audio": [{"url": "https://audio.example.com/1.mp3"}]
          }
        }
      }
    </script>
  </body>
</html>
"""


def test_extract_embedded_state():
    state = extract_embedded_state(HTML_SAMPLE)
    assert "note" in state
    assert state["note"]["noteId"] == "abc123"


def test_normalize_note_payload():
    state = extract_embedded_state(HTML_SAMPLE)
    payload = normalize_note_payload(state, source_url="https://www.xiaohongshu.com/explore/abc123")
    assert payload.note_id == "abc123"
    assert payload.title == "上海咖啡地图"
    assert payload.author == "小红薯作者"
    assert payload.tags == ["咖啡", "上海"]
    assert payload.video_urls == ["https://video.example.com/1.mp4"]


def test_parse_note_from_html():
    payload = parse_note_from_html(HTML_SAMPLE, source_url="https://example.com/note")
    assert payload.source_url == "https://example.com/note"
    assert "周末去了三家新店" in payload.content
