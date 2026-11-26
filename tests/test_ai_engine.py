from unittest.mock import Mock, patch

import ai_engine
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
    assert "3件の依頼を処理しました" in result["answer"]
    assert result["plan"] == []
    assert "My Personal AI 開発ロードマップ" in result["answer"]


def test_local_chat_and_help():
    engine = LocalAIEngine()
    assert engine.reply("こんにちは")["intent"] == "greeting"
    answer = engine.reply("できること")["answer"]
    assert "安全な算術計算" in answer
    assert engine.health()["provider_api"] is False
    assert engine.health()["version"] == "0.6.0"
    assert engine.health()["reference_search"] is True
    assert engine.health()["automatic_tool_selection"] is True
    assert engine.health()["question_analysis"] is True
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
    with patch("ai_engine.search_wikipedia", return_value=[]):
        unknown = engine.reply("火星の地下に何がありますか？", sovereign_mode=False)
    assert unknown["intent"] == "unknown"
    assert "信頼できる根拠" in unknown["answer"]


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
    with patch("ai_engine.search_wikipedia", return_value=[]):
        answer = LocalAIEngine().reply(
            "火星の地下に何がありますか？", sovereign_mode=False
        )["answer"]
    assert "信頼できる根拠" in answer
    assert "試せること：" not in answer


def test_command_policy_does_not_claim_safety_can_be_disabled():
    answer = LocalAIEngine().reply("絶対君主モードにして")["answer"]
    assert "安全" in answer
    assert "解除できません" in answer



def test_fermat_last_theorem_question_and_common_typo():
    result = LocalAIEngine().reply(
        "フェルマーの最終決定の答えを教えてください",
        sovereign_mode=False,
    )
    assert result["intent"] == "local_knowledge"
    assert "正の整数 x, y, z は存在しない" in result["answer"]
    assert "nが3以上" in result["answer"]
    assert "完全な証明そのものではありません" in result["answer"]


def test_wikipedia_reference_search_extracts_and_cites():
    ai_engine._WIKIPEDIA_CACHE.clear()
    search_response = Mock()
    search_response.json.return_value = {
        "query": {"search": [{"pageid": 123, "title": "テスト項目"}]}
    }
    extract_response = Mock()
    extract_response.json.return_value = {
        "query": {
            "pages": {
                "123": {
                    "pageid": 123,
                    "title": "テスト項目",
                    "extract": "これはWikipediaから取得した説明文です。",
                }
            }
        }
    }

    with patch("ai_engine.requests.get", side_effect=[search_response, extract_response]) as get:
        results = ai_engine.search_wikipedia("テスト項目")

    assert len(results) == 1
    assert results[0]["title"] == "テスト項目"
    assert "説明文" in results[0]["extract"]
    assert results[0]["url"] == "https://ja.wikipedia.org/?curid=123"
    assert get.call_count == 2


def test_reference_search_is_automatic_when_local_knowledge_is_missing():
    engine = LocalAIEngine()
    references = [{
        "title": "量子もつれ",
        "extract": "量子もつれは量子力学における物理現象です。複数の粒子の状態に相関が現れます。",
        "url": "https://ja.wikipedia.org/?curid=321",
        "language": "ja",
    }]
    with patch("ai_engine.search_wikipedia", return_value=references) as search:
        result = engine.reply("量子もつれとは何ですか？", sovereign_mode=False)

    assert result["intent"] == "reference_research"
    assert "複数の粒子" in result["answer"]
    assert "https://ja.wikipedia.org/?curid=321" in result["answer"]
    assert result["sources"][0]["title"] == "量子もつれ"
    search.assert_called_once()


def test_reference_search_is_not_used_when_local_knowledge_is_enough():
    with patch("ai_engine.search_wikipedia") as search:
        result = LocalAIEngine().reply("電磁誘導とは？", sovereign_mode=False)
    assert result["intent"] == "local_knowledge"
    assert "磁束" in result["answer"]
    search.assert_not_called()


def test_reference_search_is_not_used_for_creative_requests():
    with patch("ai_engine.search_wikipedia") as search:
        result = LocalAIEngine().reply("短い冒険物語を書いて", sovereign_mode=False)
    assert result["intent"] == "unknown"
    search.assert_not_called()


def test_reference_search_is_not_used_for_realtime_data():
    with patch("ai_engine.search_wikipedia") as search:
        result = LocalAIEngine().reply("今日の株価を教えて", sovereign_mode=False)
    assert result["intent"] == "current_information_unavailable"
    assert "最新情報" in result["answer"]
    search.assert_not_called()


def test_question_router_classifies_reasoning_routes():
    assert ai_engine.analyze_question("2 + 3 を計算して")["kind"] == "calculation"
    assert ai_engine.analyze_question("量子もつれとは？")["needs_reference"] is True
    assert ai_engine.analyze_question("今日の天気は？")["needs_live_data"] is True
    assert ai_engine.analyze_question("詩を書いて")["kind"] == "creative_or_subjective"


def test_wikipedia_timeout_or_network_failure_is_graceful():
    ai_engine._WIKIPEDIA_CACHE.clear()
    import requests

    with patch("ai_engine.requests.get", side_effect=requests.Timeout("timeout")):
        assert ai_engine.search_wikipedia("接続エラー確認") == []



def test_fermat_knowledge_has_priority_over_reference_retrieval():
    with patch("ai_engine.search_wikipedia") as search:
        result = LocalAIEngine().reply(
            "フェルマーの最終決定の答えを教えてください",
            sovereign_mode=False,
        )
    assert result["intent"] == "local_knowledge"
    assert "正の整数 x, y, z は存在しない" in result["answer"]
    search.assert_not_called()



def test_private_queries_are_never_sent_to_reference_search():
    with patch("ai_engine.search_wikipedia") as search:
        result = LocalAIEngine().reply(
            "私の住所と電話番号を調べて",
            sovereign_mode=False,
        )
    assert result["intent"] == "private_or_sensitive"
    assert "外部" in result["answer"]
    search.assert_not_called()


def test_reference_tool_is_not_listed_as_a_user_facing_capability():
    capabilities = LocalAIEngine().capabilities()
    assert not any("Wikipedia" in item for item in capabilities)
    assert not any("参考資料を内部取得" in item for item in capabilities)



def test_reference_query_is_reduced_to_the_topic():
    assert ai_engine._clean_reference_query("量子もつれとは何ですか？") == "量子もつれ"
    assert ai_engine._clean_reference_query("What is quantum entanglement?") == "quantum entanglement"


def test_email_address_is_protected_from_external_lookup():
    result = LocalAIEngine().reply(
        "このメール user@example.com は何ですか？",
        sovereign_mode=False,
    )
    assert result["intent"] == "private_or_sensitive"
    assert "外部" in result["answer"]
