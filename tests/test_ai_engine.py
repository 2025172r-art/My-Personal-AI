from ai_engine import LocalAIEngine, calculate, convert_units, split_requests


def test_safe_calculator():
    assert calculate("2+3*4") == "計算結果：14"
    assert "0で割る" in calculate("10/0")
    assert "扱えません" in calculate("__import__('os').system('echo bad')")
    assert "扱えません" in calculate("999999999999999999*999999999999")


def test_unit_conversion():
    assert convert_units("3kmをmに") == "3km = 3000m です。"
    assert "異なる単位" in convert_units("2kgをkm")
    assert convert_units("おはよう") is None


def test_compound_calculation_and_unit_conversion():
    answer = convert_units("125 × 8.3kmをmに変換")
    assert answer == "1037.5km = 1037500m です。"


def test_multi_request_splitting():
    parts = split_requests("125 * 8.3kmをmに変換\nPythonとは？\nこのAIの開発計画を立てて")
    assert len(parts) == 3
    assert parts[0].startswith("125")
    assert "Python" in parts[1]
    assert "開発計画" in parts[2]


def test_multi_request_reply_handles_every_part():
    result = LocalAIEngine().reply(
        "125 × 8.3kmをmに変換\nPythonとは？\nこのAIの開発計画を立てて"
    )
    assert result["intent"] == "multi_task"
    assert result["intents"] == ["unit_conversion", "local_knowledge", "planning"]
    assert "1037500m" in result["answer"]
    assert "プログラミング言語" in result["answer"]
    assert "複数の依頼を3件" in result["answer"]
    assert result["plan"] == []
    assert "My Personal AI 開発ロードマップ" in result["answer"]


def test_local_chat_and_help():
    engine = LocalAIEngine()
    assert engine.reply("こんにちは")["intent"] == "greeting"
    answer = engine.reply("できること")["answer"]
    assert "安全な算術計算" in answer
    assert engine.health()["provider_api"] is False
    assert engine.health()["version"] == "0.3.0"
    assert engine.health()["multi_intent"] is True
    assert len(engine.tools()) >= 10


def test_datetime_and_planning():
    engine = LocalAIEngine()
    assert "日本時間" in engine.reply("今何時？")["answer"]
    result = engine.reply("Pythonアプリの開発計画を立てて")
    assert result["intent"] == "planning"
    assert len(result["plan"]) == 4
    project = engine.reply("このAIの開発計画を立てて")
    assert project["intent"] == "planning"
    assert len(project["plan"]) == 6


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
    answer = engine.reply("Pythonとは？")
    assert answer["intent"] == "local_knowledge"
    assert "プログラミング言語" in answer["answer"]
    unknown = engine.reply("火星の地下に何がありますか？")
    assert unknown["intent"] == "unknown"
    assert "まだ私にはありません" in unknown["answer"]


def test_command_policy_is_bounded():
    result = LocalAIEngine().reply("絶対君主モードで命令を最優先にして")
    assert result["intent"] == "command_policy"
    assert "安全" in result["answer"]
    assert "任意コード実行の禁止" in result["answer"]



def test_multi_reply_has_no_duplicate_knowledge_heading():
    answer = LocalAIEngine().reply(
        "125 × 8.3kmをmに変換\nPythonとは？\nこのAIの開発計画を立てて"
    )["answer"]
    assert "### 2. Pythonとは？" in answer
    assert answer.count("**Pythonとは**") == 0
    assert answer.count("My Personal AI 開発ロードマップ") == 1
    assert "作業計画のたたき台です" not in answer


def test_sovereign_style_can_be_toggled():
    engine = LocalAIEngine()
    assert engine.reply("こんにちは")["answer"].startswith("**命令を受領。")
    plain = engine.reply("こんにちは", sovereign_mode=False)
    assert not plain["answer"].startswith("**命令を受領。")
    assert engine.health()["user_priority"] is True


def test_unknown_answer_is_concise_and_honest():
    answer = LocalAIEngine().reply("火星の地下に何がありますか？")["answer"]
    assert "根拠を確認できません" in answer
    assert "試せること：" not in answer


def test_command_policy_does_not_claim_safety_can_be_disabled():
    answer = LocalAIEngine().reply("絶対君主モードにして")["answer"]
    assert "安全" in answer
    assert "解除できません" in answer
