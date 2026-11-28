"""Polite, attributed bulk and on-demand ingestion from Japanese Wikipedia."""
from __future__ import annotations

import re
from typing import Any

import requests

WIKIPEDIA_API = "https://ja.wikipedia.org/w/api.php"
USER_AGENT = (
    "MyPersonalAI/1.2.0 "
    "(https://github.com/2025172r-art/My-Personal-AI; personal educational use) "
    "Python requests"
)
LICENSE = "CC BY-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"

# A one-request starter collection spanning core academic and cultural fields.
CORE_ARTICLE_TITLES = [
    "数学", "物理学", "化学", "生物学", "地球科学",
    "天文学", "情報科学", "人工知能", "歴史", "地理学",
    "経済学", "哲学", "心理学", "社会学", "法学",
    "文学", "芸術", "音楽", "環境問題", "日本",
]


def _normalise_page(page: dict[str, Any], language: str = "ja") -> dict[str, Any] | None:
    """Convert an Action API page result to a bounded, attributed cache record."""
    try:
        page_id = int(page.get("pageid", 0))
    except (TypeError, ValueError):
        return None
    title = re.sub(r"\s+", " ", str(page.get("title", "")).strip())
    extract = re.sub(r"\n{3,}", "\n\n", str(page.get("extract", "")).strip())
    extract = extract[:12000]
    if page_id <= 0 or not title or not extract:
        return None

    revisions = page.get("revisions") or []
    revision = revisions[0] if revisions and isinstance(revisions[0], dict) else {}
    try:
        revision_id = int(revision.get("revid")) if revision.get("revid") else None
    except (TypeError, ValueError):
        revision_id = None
    source_updated_at = str(revision.get("timestamp", "")) or None
    fallback_url = f"https://{language}.wikipedia.org/?curid={page_id}"
    url = str(page.get("fullurl") or fallback_url)
    if not url.startswith(f"https://{language}.wikipedia.org/"):
        url = fallback_url

    return {
        "language": language,
        "page_id": page_id,
        "title": title[:300],
        "url": url,
        "article_text": extract,
        "extract": extract,
        "revision_id": revision_id,
        "source_updated_at": source_updated_at,
        "license": LICENSE,
        "license_url": LICENSE_URL,
    }


def fetch_core_wikipedia_articles(
    titles: list[str] | None = None,
    max_chars: int = 12000,
) -> list[dict[str, Any]]:
    """Fetch a curated cross-disciplinary starter pack in one polite API request.

    This is a bounded knowledge starter, not a mirror of the entire encyclopedia.
    Requests identify the client, use maxlag, and do not run concurrently.
    """
    selected = list(dict.fromkeys(titles or CORE_ARTICLE_TITLES))[:30]
    selected = [str(title).strip()[:100] for title in selected if str(title).strip()]
    if not selected:
        return []
    try:
        response = requests.get(
            WIKIPEDIA_API,
            params={
                "action": "query",
                "prop": "extracts|info|revisions",
                "titles": "|".join(selected),
                "redirects": 1,
                "inprop": "url",
                "rvprop": "ids|timestamp",
                "explaintext": 1,
                "exsectionformat": "plain",
                "exchars": max(1000, min(int(max_chars), 12000)),
                "format": "json",
                "formatversion": 2,
                "maxlag": 5,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=(5, 25),
        )
        response.raise_for_status()
        payload = response.json()
        pages = payload.get("query", {}).get("pages", [])
        if not isinstance(pages, list):
            return []
        results = []
        for page in pages:
            if not isinstance(page, dict) or page.get("missing"):
                continue
            item = _normalise_page(page)
            if item:
                results.append(item)
        return results
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return []


def wikipedia_search_terms(query: str, max_terms: int = 24) -> list[str]:
    """Create short Japanese bigrams and English words for cached-page matching."""
    terms: list[str] = []
    stop_words = {
        "とは", "って何", "教えて", "ください", "について", "知りたい",
        "説明", "何ですか", "please", "what", "when", "where", "how",
        "does", "this", "that", "with", "from", "about",
    }
    for piece in re.findall(r"[a-z0-9][a-z0-9_-]*|[ぁ-んァ-ン一-龥]+", (query or "").lower()):
        if piece in stop_words or len(piece) < 2:
            continue
        if re.fullmatch(r"[a-z0-9][a-z0-9_-]*", piece):
            terms.append(piece)
        else:
            terms.append(piece)
            terms.extend(piece[index:index + 2] for index in range(len(piece) - 1))
    return list(dict.fromkeys(term for term in terms if len(term) >= 2))[:max_terms]
