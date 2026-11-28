from unittest.mock import Mock, patch

from wikipedia_brain import fetch_core_wikipedia_articles, wikipedia_search_terms


def test_wikipedia_bulk_fetch_uses_one_polite_multi_title_request():
    response = Mock()
    response.json.return_value = {
        "query": {
            "pages": [
                {
                    "pageid": 101,
                    "title": "数学",
                    "fullurl": "https://ja.wikipedia.org/wiki/数学",
                    "extract": "数学は数や図形、構造、変化などを研究する学問です。",
                    "revisions": [{"revid": 901, "timestamp": "2026-11-27T00:00:00Z"}],
                },
                {
                    "pageid": 102,
                    "title": "化学",
                    "fullurl": "https://ja.wikipedia.org/wiki/化学",
                    "extract": "化学は物質の構造や性質、変化を研究する学問です。",
                    "revisions": [{"revid": 902, "timestamp": "2026-11-27T00:00:00Z"}],
                },
                {"title": "削除済み記事", "missing": True},
            ]
        }
    }

    with patch("wikipedia_brain.requests.get", return_value=response) as get:
        pages = fetch_core_wikipedia_articles(["数学", "化学"], max_chars=5000)

    assert len(pages) == 2
    assert pages[0]["page_id"] == 101
    assert pages[0]["revision_id"] == 901
    assert pages[0]["license"] == "CC BY-SA 4.0"
    assert pages[0]["url"] == "https://ja.wikipedia.org/wiki/数学"
    assert get.call_count == 1
    args, kwargs = get.call_args
    assert kwargs["params"]["titles"] == "数学|化学"
    assert kwargs["params"]["maxlag"] == 5
    assert "MyPersonalAI/1.2.0" in kwargs["headers"]["User-Agent"]


def test_wikipedia_fetch_failure_is_graceful():
    import requests

    with patch("wikipedia_brain.requests.get", side_effect=requests.Timeout("timeout")):
        assert fetch_core_wikipedia_articles(["数学"]) == []


def test_japanese_wikipedia_search_terms_use_bigrams():
    terms = wikipedia_search_terms("量子もつれとは何ですか？")
    assert "量子" in terms
    assert "もつ" in terms
    assert len(terms) <= 24
