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
