from ai_engine import LocalAIEngine, calculate, convert_units


def test_safe_calculator():
    assert calculate("2+3*4") == "計算結果：14"
    assert "0で割る" in calculate("10/0")
    assert "扱えません" in calculate("__import__('os').system('echo bad')")
    assert "扱えません" in calculate("999999999999999999*999999999999")


def test_unit_conversion():
    assert convert_units("3kmをmに") == "3km = 3000m です。"
    assert "異なる単位" in convert_units("2kgをkm")
    assert convert_units("おはよう") is None


def test_local_chat_and_help():
    engine = LocalAIEngine()
    assert engine.reply("こんにちは")["intent"] == "greeting"
    answer = engine.reply("できること")["answer"]
    assert "安全な算術計算" in answer
    assert engine.health()["provider_api"] is False
    assert len(engine.tools()) >= 8


def test_datetime_and_planning():
    engine = LocalAIEngine()
    assert "日本時間" in engine.reply("今何時？")["answer"]
    result = engine.reply("Pythonアプリの開発計画を立てて")
    assert result["intent"] == "planning"
    assert len(result["plan"]) == 4


def test_memory_search():
    engine = LocalAIEngine()
    result = engine.reply(
        "前に登録したPythonの好みを覚えている？",
        memories=[{"category": "好み", "content": "Pythonで作るのが好き"}],
    )
    assert result["intent"] == "memory_search"
    assert "Pythonで作るのが好き" in result["answer"]


def test_document_summary_and_search():
    engine = LocalAIEngine()
    document = "最初の重要な文章です。これは2番目の文章です。最後に結論を書きます。"
    summary = engine.reply("この資料を要約して", document_context=document)
    assert summary["intent"] == "summarize"
    assert "重要な文章" in summary["answer"]
    search = engine.reply("この資料に何と書いてある？", document_context=document)
    assert search["intent"] == "document_search"


def test_knowledge_and_unknown():
    engine = LocalAIEngine()
    assert engine.reply("Pythonとは？")["intent"] == "local_knowledge"
    unknown = engine.reply("火星の地下に何がありますか？")
    assert unknown["intent"] == "unknown"
    assert "まだ私にはありません" in unknown["answer"]
