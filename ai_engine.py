from __future__ import annotations

import ast
import operator
import re
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_math_node(node: ast.AST) -> float | int:
    if isinstance(node, ast.Expression):
        return _safe_math_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _safe_math_node(node.left)
        right = _safe_math_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 8:
            raise ValueError("指数は -8 から 8 の範囲にしてください。")
        result = _BINARY_OPERATORS[type(node.op)](left, right)
        if abs(result) > 10**15:
            raise ValueError("計算結果が大きすぎます。")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_safe_math_node(node.operand))
    raise ValueError("使える演算子は + - * / // % ** と括弧だけです。")


def calculate(expression: str) -> str:
    """Evaluate a small arithmetic expression without eval or code execution."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_math_node(tree)
    except ZeroDivisionError:
        return "0で割ることはできません。"
    except (SyntaxError, ValueError, TypeError, OverflowError):
        return "その計算式は扱えません。数字と + - * / // % **、括弧を使ってください。"
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return f"計算結果：{result}"


def _tokens(text: str) -> set[str]:
    normalized = text.lower()
    tokens = set(re.findall(r"[a-z0-9_]{2,}|[ぁ-んァ-ン一-龥]+", normalized))
    for token in list(tokens):
        if re.fullmatch(r"[ぁ-んァ-ン一-龥]+", token):
            tokens.update(token[i:i + 2] for i in range(max(0, len(token) - 1)))
    return tokens


def _sentence_summary(text: str, max_sentences: int = 5) -> str:
    sentences = [
        part.strip()
        for part in re.split(r"(?<=[。！？.!?])\s*|\n+", text)
        if len(part.strip()) >= 8
    ]
    if not sentences:
        return text.strip()[:900] or "要約できる文章がありません。"
    if len(sentences) <= max_sentences:
        return "\n".join(f"・{sentence}" for sentence in sentences[:max_sentences])

    word_counts: Counter[str] = Counter()
    sentence_tokens = [_tokens(sentence) for sentence in sentences]
    for group in sentence_tokens:
        word_counts.update(group)
    scored = []
    for index, group in enumerate(sentence_tokens):
        score = sum(1 / word_counts[token] for token in group)
        scored.append((score, index, sentences[index]))
    chosen = sorted(scored, reverse=True)[:max_sentences]
    chosen.sort(key=lambda item: item[1])
    return "\n".join(f"・{item[2]}" for item in chosen)


def _find_calculation(text: str) -> str | None:
    match = re.search(
        r"(?<![\w.])(\d+(?:\.\d+)?(?:\s*(?:\*\*|[+\-*/%])\s*\d+(?:\.\d+)?)+)(?![\w.])",
        text,
    )
    return match.group(1).replace(" ", "") if match else None


def _search_memories(query: str, memories: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    query_tokens = _tokens(query)
    ranked = []
    for item in memories:
        content = f"{item.get('category', '')} {item.get('content', '')}"
        content_tokens = _tokens(content)
        overlap = len(query_tokens & content_tokens)
        if overlap:
            ranked.append((overlap, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in ranked[:limit]]


def _plan_for(request: str) -> list[str]:
    text = request.lower()
    if any(word in text for word in ("プログラム", "python", "アプリ", "開発", "コード", "webサイト")):
        return [
            "目的と必要な機能を整理する",
            "小さな部品に分けて実装する",
            "入力例・異常な入力を含めてテストする",
            "結果を確認して改善点を記録する",
        ]
    if any(word in text for word in ("勉強", "学習", "宿題", "試験", "テスト勉強")):
        return [
            "分からない範囲を具体的に書き出す",
            "基本概念と例を確認する",
            "短い問題を解いて理解を確かめる",
            "間違えた部分を復習する",
        ]
    if any(word in text for word in ("文章", "レポート", "作文", "発表", "企画")):
        return [
            "目的と読者を決める",
            "伝えたい要点を3つ以内に整理する",
            "構成に沿って下書きを作る",
            "事実・表現・誤字を見直す",
        ]
    return [
        "依頼のゴールと条件を整理する",
        "必要な情報や材料を集める",
        "実行できる小さな手順に分ける",
        "結果を確認し、次の改善点を決める",
    ]


class LocalAIEngine:
    """A transparent, rule-based Japanese assistant that runs without model APIs."""

    name = "My Personal AI Local Engine"
    version = "0.1.0"

    def capabilities(self) -> list[str]:
        return [
            "日本語の基本会話とヘルプ",
            "安全な算術計算",
            "日本時間の日付・時刻",
            "登録済み長期記憶のキーワード検索",
            "アップロード文書の抽出的な要約",
            "目的別の作業計画",
            "入力文の文字数・単語数の確認",
        ]

    def reply(
        self,
        request: str,
        history: list[dict[str, Any]] | None = None,
        memories: list[dict[str, Any]] | None = None,
        document_context: str = "",
    ) -> dict[str, Any]:
        text = request.strip()
        history = history or []
        memories = memories or []
        if not text:
            return {"answer": "メッセージを入力してください。", "plan": [], "intent": "empty"}

        lowered = text.lower()

        if any(word in lowered for word in ("できること", "使い方", "ヘルプ", "help", "機能一覧")):
            lines = "\n".join(f"・{item}" for item in self.capabilities())
            return {
                "answer": "今の自作エンジンでできることです。\n" + lines
                + "\n\nまだ自由な文章生成や最新情報の検索はできません。機能は少しずつ追加できます。",
                "plan": [],
                "intent": "help",
            }

        if re.search(r"^(こんにちは|おはよう|こんばんは|やあ|はじめまして)[！!。 ]*$", text):
            return {
                "answer": "こんにちは！私はAPIを使わずPythonのルールと機能で動く、My Personal AIの初期エンジンです。計算・記憶検索・資料要約・作業計画を手伝えます。「できること」と入力すると機能一覧を表示します。",
                "plan": [],
                "intent": "greeting",
            }

        if any(word in text for word in ("今何時", "現在時刻", "今日の日付", "今日は何日", "今日何日")):
            now = datetime.now(ZoneInfo("Asia/Tokyo"))
            return {
                "answer": f"日本時間は {now:%Y年%m月%d日 %H:%M} です。",
                "plan": [],
                "intent": "datetime",
            }

        expression = _find_calculation(text)
        if expression and (
            any(symbol in text for symbol in ("+", "-", "*", "/", "%"))
            or any(word in text for word in ("計算", "いくつ", "は？", "は?"))
        ):
            return {"answer": calculate(expression), "plan": [], "intent": "calculation"}

        if any(word in text for word in ("要約", "まとめて", "要点")):
            source = document_context.strip()
            if not source:
                return {
                    "answer": "要約する文章がありません。先に「ファイル・音声」タブで対応ファイルを読み込むか、要約したい文章をメッセージに貼り付けて「この文章を要約」と送ってください。",
                    "plan": [],
                    "intent": "summarize",
                }
            return {
                "answer": "資料から重要そうな文を抜き出した要約です（新しい文章を生成しているのではなく、原文の文を選んでいます）。\n"
                + _sentence_summary(source),
                "plan": [],
                "intent": "summarize",
            }

        if any(word in text for word in ("計画", "手順", "段取り", "どう進め", "予定を立て")):
            plan = _plan_for(text)
            return {
                "answer": "作業計画のたたき台です。\n" + "\n".join(
                    f"{index}. {step}" for index, step in enumerate(plan, 1)
                ) + "\n\n内容に合わせて順番や項目を調整してください。",
                "plan": plan,
                "intent": "planning",
            }

        if any(word in text for word in ("覚えている", "記憶して", "保存した記憶", "前に登録")):
            matches = _search_memories(text, memories)
            if matches:
                answer = "関連しそうな登録済み記憶です。\n" + "\n".join(
                    f"・[{item.get('category', 'その他')}] {item.get('content', '')}"
                    for item in matches
                )
            else:
                answer = "関連する登録済み記憶は見つかりませんでした。長期記憶タブから情報を登録できます。"
            return {"answer": answer, "plan": [], "intent": "memory_search"}

        if any(word in text for word in ("文字数", "単語数", "何文字")):
            compact = re.sub(r"\s", "", text)
            english_words = re.findall(r"[A-Za-z0-9_]+", text)
            return {
                "answer": f"このメッセージは空白を除いて {len(compact)} 文字、英数字の単語は {len(english_words)} 個です。",
                "plan": [],
                "intent": "text_stats",
            }

        # A small transparent knowledge base is preferable to inventing an answer.
        local_facts = [
            (("pythonとは", "pythonって何"), "Pythonは、読みやすい文法を特徴とするプログラミング言語です。このアプリでは、会話の分類や計算、記憶検索などの処理をPythonで実行します。"),
            (("supabaseとは", "supabaseって何"), "Supabaseは、データベースなどのバックエンド機能を提供するサービスです。このアプリでは会話履歴と長期記憶の保存先として使っています。"),
            (("renderとは", "renderって何"), "Renderは、GitHubなどのコードからWebアプリを公開できるホスティングサービスです。このアプリのStreamlit画面を動かしています。"),
            (("aiとは", "人工知能とは"), "AI（人工知能）は、認識・分類・予測・計画・文章処理など、人が知的に行う作業の一部をコンピューターで扱う技術の総称です。"),
        ]
        for triggers, answer in local_facts:
            if any(trigger in lowered for trigger in triggers):
                return {"answer": answer, "plan": [], "intent": "local_knowledge"}

        matches = _search_memories(text, memories, limit=3)
        if matches:
            return {
                "answer": "質問に関係しそうな登録済み情報を見つけました。\n"
                + "\n".join(f"・{item.get('content', '')}" for item in matches)
                + "\n\nこの情報を使った回答が必要なら、もう少し具体的に質問してください。",
                "plan": [],
                "intent": "memory_context",
            }

        if document_context and any(word in text for word in ("資料", "ファイル", "この文書", "この文章")):
            return {
                "answer": "読み込まれている資料の一部です。内容を指定して質問してください。\n\n"
                + document_context[:1200],
                "plan": [],
                "intent": "document_context",
            }

        previous = ""
        if history:
            last = history[-1]
            if last.get("role") == "assistant":
                previous = str(last.get("content", ""))[:160]
        suffix = f"\n\n直前の回答メモ：{previous}" if previous else ""
        return {
            "answer": (
                "まだこの質問に答える機能を持っていません。私は現在、Pythonのルール・小さな知識集・登録済み記憶を使うローカルAIです。"
                "分からない内容を知っているふりはしません。\n\n"
                "試せる例：\n"
                "・計算して 125 * 8\n"
                "・今日の日付を教えて\n"
                "・この資料を要約して（先にファイルを読み込む）\n"
                "・Pythonとは？\n"
                "・このプロジェクトの計画を立てて\n"
                "・できること"
                + suffix
            ),
            "plan": [],
            "intent": "unknown",
        }


def run_agent_task(
    client: Any = None,
    user_request: str = "",
    history: list[dict[str, Any]] | None = None,
    memories: list[dict[str, Any]] | None = None,
    document_context: str = "",
    use_web_search: bool = False,
    use_multi_agent: bool = False,
) -> dict[str, Any]:
    """Backward-compatible entry point; intentionally does not call a model API."""
    del client, use_web_search, use_multi_agent
    return LocalAIEngine().reply(
        request=user_request,
        history=history,
        memories=memories,
        document_context=document_context,
    )
