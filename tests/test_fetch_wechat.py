from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent / "scripts"))

from fetch_wechat import ParseError, extract_article_fields


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_extract_article_fields_from_fixture() -> None:
    html = read_fixture("wechat_article.html")
    article = extract_article_fields(html, "https://mp.weixin.qq.com/s?__biz=abc&mid=1&sn=wx123")
    assert article["note_id"] == "wx123"
    assert article["title"] == "Spring Product Notes"
    assert article["author"]["name"] == "Growth Lab"
    assert article["content"].startswith("This week we reviewed three skincare products.")
    assert article["images"] == [
        "https://mmbiz.qpic.cn/example-image-1",
        "https://mmbiz.qpic.cn/example-image-2",
    ]
    assert article["published_at"].startswith("2024-06-01T")
    assert article["source_type"] == "wechat"


def test_extract_article_fields_raises_for_missing_content() -> None:
    with pytest.raises(ParseError):
        extract_article_fields("<html><body>missing content</body></html>", "https://mp.weixin.qq.com/s?a=1")
