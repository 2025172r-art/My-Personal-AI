from memory.store import MemoryStore


def test_sqlite_memory_and_chat_round_trip(tmp_path):
    store = MemoryStore(sqlite_path=tmp_path / "memory.sqlite3")

    store.add_message("test-session", "user", "こんにちは")
    messages = store.get_messages("test-session")
    assert len(messages) == 1
    assert messages[0]["content"] == "こんにちは"

    store.add_memory("好み", "回答は日本語がよい")
    memories = store.get_memories()
    assert len(memories) == 1
    assert memories[0]["content"] == "回答は日本語がよい"

    store.delete_memory(memories[0]["id"])
    assert store.get_memories() == []



def test_wikipedia_pages_are_persisted_separately_and_searchable(tmp_path):
    store = MemoryStore(sqlite_path=tmp_path / "wiki.sqlite3")
    pages = [
        {
            "language": "ja",
            "page_id": 1001,
            "title": "光合成",
            "url": "https://ja.wikipedia.org/?curid=1001",
            "extract": "光合成は、植物などが光エネルギーを使って有機物を作る過程です。",
            "revision_id": 88,
            "source_updated_at": "2026-11-27T00:00:00Z",
            "license": "CC BY-SA 4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        },
        {
            "language": "ja",
            "page_id": 1002,
            "title": "細胞",
            "url": "https://ja.wikipedia.org/?curid=1002",
            "extract": "細胞は生物を構成する基本単位です。",
        },
        {
            "language": "ja",
            "page_id": 1003,
            "title": "偽サイト",
            "url": "https://example.com/article",
            "extract": "保存してはいけないURLです。",
        },
    ]

    assert store.upsert_wikipedia_pages(pages) == 2
    assert store.get_wikipedia_stats()["count"] == 2

    results = store.search_wikipedia_pages("光合成とは何ですか？", limit=5)
    assert results
    assert results[0]["title"] == "光合成"
    assert "光エネルギー" in results[0]["extract"]
    assert results[0]["license"] == "CC BY-SA 4.0"

    # Re-import updates the existing article instead of creating a duplicate.
    updated = {**pages[0], "extract": "光合成では光エネルギーが使われます。"}
    assert store.upsert_wikipedia_pages([updated]) == 1
    assert store.get_wikipedia_stats()["count"] == 2
    assert "光エネルギー" in store.search_wikipedia_pages("光合成", 1)[0]["extract"]
