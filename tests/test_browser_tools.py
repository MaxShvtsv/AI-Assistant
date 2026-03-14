import importlib
import sys


sys.path.insert(0, "app")

browser = importlib.import_module("tools.browser")


def test_build_google_search_url() -> None:
    result = browser._build_google_search_url("intel assistant")

    assert result == "https://www.google.com/search?q=intel+assistant"


def test_build_youtube_music_search_url() -> None:
    result = browser._build_youtube_music_search_url("daft punk")

    assert result == "https://music.youtube.com/search?q=daft+punk"


def test_normalize_url_adds_scheme() -> None:
    assert browser._normalize_url("music.youtube.com") == "https://music.youtube.com"
    assert browser._normalize_url("https://example.com") == "https://example.com"
