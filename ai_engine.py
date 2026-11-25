from __future__ import annotations

import ast
import math
import operator
import re
from collections import Counter
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

# Arithmetic is evaluated from an allow-list of AST nodes. No eval/exec is used.
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

UNIT_TABLE = {
    "mm": ("length", 0.001, "mm"),
    "cm": ("length", 0.01, "cm"),
    "m": ("length", 1.0, "m"),
    "km": ("length", 1000.0, "km"),
    "mg": ("mass", 0.001, "mg"),
    "g": ("mass", 1.0, "g"),
    "kg": ("mass", 1000.0, "kg"),
    "ml": ("volume", 0.001, "mL"),
    "l": ("volume", 1.0, "L"),
}

KNOWLEDGE = [
    {
        "title": "Pythonとは",
        "triggers": ["pythonとは", "pythonって何", "pythonとは何", "python 言語"],
        "answer": "Pythonは、読みやすい文法を特徴とするプログラミング言語です。Webアプリ、データ分析、自動化、教育など幅広い用途に使われます。",
    },
    {
        "title": "人工知能とは",
        "triggers": ["aiとは", "人工知能とは", "aiって何"],
        "answer": "AI（人工知能）は、認識・分類・予測・計画・文章処理など、人が知的に行う作業の一部をコンピューターで扱う技術の総称です。",
    },
    {
        "title": "機械学習とは",
        "triggers": ["機械学習とは", "machine learning", "機械学習って何"],
        "answer": "機械学習は、データからパターンを学び、分類や予測などに利用する方法です。学習用データと評価用データを分け、未知データで性能を確かめます。",
    },
    {
        "title": "ニューラルネットワークとは",
        "triggers": ["ニューラルネットワークとは", "ニューラルネットワークって何"],
        "answer": "ニューラルネットワークは、重み付きの計算ノードを層状につないだモデルです。学習では予測と正解のずれを使って重みを調整します。",
    },
    {
        "title": "ローカルAIとは",
        "triggers": ["ローカルaiとは", "ローカル ai", "apiなし ai"],
        "answer": "ローカルAIは、利用者の端末や管理するサーバー内で処理を行うAIの構成です。モデルのサイズや計算資源によって、できる処理の範囲が変わります。",
    },
    {
        "title": "Renderとは",
        "triggers": ["renderとは", "renderって何"],
        "answer": "Renderは、GitHubなどのコードからWebアプリを公開できるホスティングサービスです。このプロジェクトではStreamlitのPythonアプリを動かします。",
    },
    {
        "title": "Supabaseとは",
        "triggers": ["supabaseとは", "supabaseって何"],
        "answer": "Supabaseは、Postgresデータベースなどのバックエンド機能を提供するサービスです。このプロジェクトでは会話履歴と長期記憶の保存先として使います。",
    },
    {
        "title": "安全なパスワード",
        "triggers": ["安全なパスワード", "パスワードの作り方"],
        "answer": "長く、他のサービスと使い回さず、推測しにくいパスワードを使います。パスワードやAPIキーをチャット、コード、公開リポジトリに貼らないでください。",
    },
]

STOP_WORDS = {
    "です", "ます", "する", "した", "して", "これ", "それ", "あれ", "こと",
    "もの", "ため", "から", "まで", "について", "教えて", "ください", "お願い",
    "とは", "って", "何", "どの", "どんな", "ある", "いる", "でした",
}


def _safe_math_node(node: ast.AST, depth: int = 0) -> float | int:
    if depth > 20:
        raise ValueError("式が複雑すぎます。")
    if isinstance(node, ast.Expression):
        return _safe_math_node(node.body, depth + 1)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        if len(str(node.value)) > 14:
            raise ValueError("数値が大きすぎます。")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _safe_math_node(node.left, depth + 1)
        right = _safe_math_node(node.right, depth + 1)
        if isinstance(node.op, ast.Pow) and (abs(right) > 8 or abs(left) > 10**4):
            raise ValueError("べき乗の値が大きすぎます。")
        result = _BINARY_OPERATORS[type(node.op)](left, right)
        if not math.isfinite(float(result)) or abs(result) > 10**15:
            raise ValueError("計算結果が大きすぎます。")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_safe_math_node(node.operand, depth + 1))
    raise ValueError("使える演算子は + - * / // % ** と括弧だけです。")


def calculate(expression: str) -> str:
    """Evaluate bounded arithmetic without evaluating arbitrary Python code."""
    if not expression or len(expression) > 160:
        return "計算式が空、または長すぎます。"
    try:
        tree = ast.parse(expression, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 40:
            raise ValueError("式が複雑すぎます。")
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
            tokens.update(token[i:i + 2] for i in range(len(token) - 1))
    return {token for token in tokens if token not in STOP_WORDS and len(token) > 1}


def _sentences(text: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"(?<=[。！？.!?])\s*|\n+", text)
        if len(item.strip()) >= 5
    ]


def _sentence_summary(text: str, max_sentences: int = 5) -> str:
    sentences = _sentences(text)
    if not sentences:
        return text.strip()[:900] or "要約できる文章がありません。"
    if len(sentences) <= max_sentences:
        return "\n".join(f"・{sentence}" for sentence in sentences)
    counts: Counter[str] = Counter()
    groups = [_tokens(sentence) for sentence in sentences]
    for group in groups:
        counts.update(group)
    scored = [
        (sum(1 / counts[token] for token in group) if group else 0, index, sentences[index])
        for index, group in enumerate(groups)
    ]
    selected = sorted(sorted(scored, key=lambda row: (-row[0], row[1]))[:max_sentences], key=lambda row: row[1])
    return "\n".join(f"・{row[2]}" for row in selected)


def _rank_sentences(query: str, text: str, limit: int = 4) -> list[str]:
    query_terms = _tokens(query)
    sentences = _sentences(text)
    ranked = []
    for index, sentence in enumerate(sentences):
        sentence_terms = _tokens(sentence)
        overlap = len(query_terms & sentence_terms)
        if overlap:
            score = overlap / max(1, len(query_terms))
            ranked.append((score, index, sentence))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in ranked[:limit]]


def _search_memories(query: str, memories: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    query_tokens = _tokens(query)
    ranked = []
    for item in memories:
        if item.get("category") in {"タスク", "完了タスク"}:
            continue
        content = f"{item.get('category', '')} {item.get('content', '')}"
        overlap = len(query_tokens & _tokens(content))
        if overlap:
            ranked.append((overlap / max(1, len(query_tokens)), overlap, item))
    ranked.sort(key=lambda row: (-row[0], -row[1]))
    return [row[2] for row in ranked[:limit]]


def _find_calculation(text: str) -> str | None:
    normalized = text.replace("×", "*").replace("÷", "/")
    normalized = re.sub(r"(\d)\s*かける\s*(\d)", r"\1*\2", normalized)
    normalized = re.sub(r"(\d)\s*わる\s*(\d)", r"\1/\2", normalized)
    normalized = re.sub(r"(\d)\s*たす\s*(\d)", r"\1+\2", normalized)
    normalized = re.sub(r"(\d)\s*ひく\s*(\d)", r"\1-\2", normalized)
    match = re.search(
        r"(?<![\w.])(\d+(?:\.\d+)?(?:\s*(?:\*\*|[+\-*/%])\s*\d+(?:\.\d+)?)+)(?![\w.])",
        normalized,
    )
    return match.group(1).replace(" ", "") if match else None


def convert_units(text: str) -> str | None:
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(km|cm|mm|m|kg|mg|g|ml|l)\s*(?:を|から)?\s*(km|cm|mm|m|kg|mg|g|ml|l)",
        text.lower(),
    )
    if not match:
        return None
    value = float(match.group(1))
    source, target = match.group(2), match.group(3)
    source_info, target_info = UNIT_TABLE[source], UNIT_TABLE[target]
    if source_info[0] != target_info[0]:
        return f"{source}と{target}は異なる単位の種類なので変換できません。"
    result = value * source_info[1] / target_info[1]
    return f"{value:g}{source_info[2]} = {result:g}{target_info[2]} です。"


def _plan_for(request: str) -> list[str]:
    text = request.lower()
    if any(word in text for word in ("python", "プログラム", "アプリ", "開発", "コード", "webサイト")):
        return [
            "目的と利用者、必要な機能を整理する",
            "機能を小さな部品に分けて実装する",
            "通常入力と異常入力を含めてテストする",
            "結果を確認し、改善点を記録する",
        ]
    if any(word in text for word in ("勉強", "学習", "宿題", "試験", "復習")):
        return [
            "学習する範囲と期限を確認する",
            "基本概念と例を読み直す",
            "短い練習問題で理解を確認する",
            "間違えた部分を復習する",
        ]
    if any(word in text for word in ("文章", "レポート", "作文", "発表", "企画")):
        return [
            "目的と読者を決める",
            "伝える要点と根拠を整理する",
            "構成に沿って下書きを作る",
            "事実・表現・誤字を見直す",
        ]
    return [
        "依頼の目的と完了条件を整理する",
        "必要な情報や材料を集める",
        "安全な小さな手順に分けて進める",
        "結果を確認し、次の改善点を決める",
    ]


class LocalAIEngine:
    """Transparent, rule-based Japanese agent. No model/provider API is called."""

    name = "My Personal AI Local Engine"
    version = "0.2.0"

    def capabilities(self) -> list[str]:
        return [
            "日本語の基本会話・ヘルプ",
            "安全な算術計算（式の制限と入力検査付き）",
            "長さ・重さ・容量の単位変換",
            "日本時間の日付・時刻",
            "長期記憶のキーワード検索",
            "ファイル内の関連文検索と抽出的な要約",
            "目的別の作業計画",
            "文字数・英単語数の確認",
            "小さな内蔵知識ベースからの回答",
        ]

    def tools(self) -> list[dict[str, str]]:
        return [
            {"name": "calculator", "description": "四則演算・括弧・剰余・べき乗"},
            {"name": "unit_converter", "description": "長さ・重さ・容量の単位変換"},
            {"name": "japan_clock", "description": "日本時間の日付と時刻"},
            {"name": "memory_search", "description": "保存済みの記憶をキーワード検索"},
            {"name": "document_search", "description": "読み込んだ資料の関連文検索"},
            {"name": "extractive_summary", "description": "原文から重要文を抜き出す要約"},
            {"name": "task_planner", "description": "目的別の作業計画を作成"},
            {"name": "text_analyzer", "description": "文字数・英単語数を数える"},
            {"name": "local_knowledge", "description": "内蔵知識ベースを検索"},
        ]

    def health(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "provider_api": False,
            "capabilities": len(self.capabilities()),
            "tools": len(self.tools()),
        }

    def _knowledge_answer(self, request: str) -> str | None:
        lowered = request.lower()
        for item in KNOWLEDGE:
            if any(trigger in lowered for trigger in item["triggers"]):
                return f"**{item['title']}**\n{item['answer']}"
        query_terms = _tokens(request)
        if not query_terms:
            return None
        ranked = []
        for item in KNOWLEDGE:
            terms = _tokens(item["title"] + " " + " ".join(item["triggers"]) + " " + item["answer"])
            overlap = len(query_terms & terms)
            if overlap:
                ranked.append((overlap / len(query_terms), overlap, item))
        ranked.sort(key=lambda row: (-row[0], -row[1]))
        if ranked and ranked[0][0] >= 0.35:
            item = ranked[0][2]
            return f"**{item['title']}**\n{item['answer']}"
        return None

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
            return {"answer": "メッセージを入力してください。", "plan": [], "intent": "empty", "tools_used": []}
        lowered = text.lower()

        if any(word in lowered for word in ("できること", "使い方", "ヘルプ", "help", "機能一覧")):
            return {
                "answer": "今の自作AIエンジンで利用できる機能です。\n"
                + "\n".join(f"・{item}" for item in self.capabilities())
                + "\n\nこのエンジンはAPIを使わないルールベース方式です。自由な文章生成や最新Web検索はまだできません。",
                "plan": [], "intent": "help", "tools_used": [],
            }

        if re.search(r"^(こんにちは|おはよう|こんばんは|やあ|はじめまして)[！!。 ]*$", text):
            return {
                "answer": "こんにちは！私はPythonで動くMy Personal AIです。計算、単位変換、記憶検索、資料検索・要約、作業計画などを手伝えます。「できること」と入力すると機能一覧を表示します。",
                "plan": [], "intent": "greeting", "tools_used": [],
            }

        if any(word in text for word in ("今何時", "現在時刻", "今日の日付", "今日は何日", "今日何日")):
            now = datetime.now(ZoneInfo("Asia/Tokyo"))
            return {
                "answer": f"日本時間は {now:%Y年%m月%d日 %H:%M} です。",
                "plan": [], "intent": "datetime", "tools_used": ["japan_clock"],
            }

        converted = convert_units(text)
        if converted:
            return {"answer": converted, "plan": [], "intent": "unit_conversion", "tools_used": ["unit_converter"]}

        expression = _find_calculation(text)
        if expression and (
            any(symbol in text for symbol in ("+", "-", "*", "/", "%", "×", "÷"))
            or any(word in text for word in ("計算", "いくつ", "かける", "わる", "たす", "ひく"))
        ):
            return {"answer": calculate(expression), "plan": [], "intent": "calculation", "tools_used": ["calculator"]}

        if any(word in text for word in ("要約", "まとめて", "要点")):
            source = document_context.strip()
            if not source:
                return {
                    "answer": "要約する文章がありません。先に「ファイル」タブで対応ファイルを読み込むか、文章をメッセージに貼り付けてください。",
                    "plan": [], "intent": "summarize", "tools_used": [],
                }
            return {
                "answer": "資料から重要そうな文を抜き出した要約です（新しい文章を生成するのではなく、原文の文を選んでいます）。\n"
                + _sentence_summary(source),
                "plan": [], "intent": "summarize", "tools_used": ["extractive_summary"],
            }

        if document_context and any(word in text for word in ("資料", "ファイル", "この文書", "この文章", "書いてある")):
            matches = _rank_sentences(text, document_context)
            if matches:
                return {
                    "answer": "読み込んだ資料から、質問に関連する文を見つけました。\n"
                    + "\n".join(f"・{item}" for item in matches)
                    + "\n\nこれは原文からの抜き出しです。資料に書かれていない内容は補っていません。",
                    "plan": [], "intent": "document_search", "tools_used": ["document_search"],
                }
            return {
                "answer": "資料は読み込まれていますが、質問と一致する語句を含む文は見つかりませんでした。別の言葉で質問してみてください。",
                "plan": [], "intent": "document_search", "tools_used": ["document_search"],
            }

        if any(word in text for word in ("計画", "手順", "段取り", "どう進め", "予定を立て", "スケジュール")):
            plan = _plan_for(text)
            return {
                "answer": "作業計画のたたき台です。\n"
                + "\n".join(f"{index}. {step}" for index, step in enumerate(plan, 1))
                + "\n\n内容や期限に合わせて調整してください。",
                "plan": plan, "intent": "planning", "tools_used": ["task_planner"],
            }

        if any(word in text for word in ("覚えている", "記憶して", "保存した記憶", "前に登録", "覚えてる")):
            matches = _search_memories(text, memories)
            answer = (
                "関連しそうな登録済み記憶です。\n"
                + "\n".join(f"・[{item.get('category', 'その他')}] {item.get('content', '')}" for item in matches)
                if matches
                else "関連する登録済み記憶は見つかりませんでした。長期記憶タブから情報を登録できます。"
            )
            return {"answer": answer, "plan": [], "intent": "memory_search", "tools_used": ["memory_search"]}

        if any(word in text for word in ("文字数", "単語数", "何文字")):
            compact = re.sub(r"\s", "", text)
            english_words = re.findall(r"[A-Za-z0-9_]+", text)
            return {
                "answer": f"このメッセージは空白を除いて {len(compact)} 文字、英数字の単語は {len(english_words)} 個です。",
                "plan": [], "intent": "text_analysis", "tools_used": ["text_analyzer"],
            }

        knowledge = self._knowledge_answer(text)
        if knowledge:
            return {"answer": knowledge, "plan": [], "intent": "local_knowledge", "tools_used": ["local_knowledge"]}

        related_memories = _search_memories(text, memories, limit=3)
        if related_memories:
            return {
                "answer": "質問に関係しそうな登録済み情報を見つけました。\n"
                + "\n".join(f"・[{item.get('category', 'その他')}] {item.get('content', '')}" for item in related_memories)
                + "\n\nこれは保存済み情報の検索結果です。ほかに確認したい点があれば具体的に質問してください。",
                "plan": [], "intent": "memory_context", "tools_used": ["memory_search"],
            }

        return {
            "answer": (
                "この質問に答えるための知識や機能が、まだ私にはありません。私は外部の生成AI APIを使わないPython製エンジンなので、知らないことを自由に文章生成することはできません。\n\n"
                "試せること：\n"
                "・計算して 125 * 8\n"
                "・3kmをmに変換\n"
                "・今日の日付を教えて\n"
                "・この資料を要約して（先にファイルを読み込む）\n"
                "・Pythonとは？\n"
                "・このプロジェクトの計画を立てて\n"
                "・覚えていることを教えて\n"
                "・できること"
            ),
            "plan": [], "intent": "unknown", "tools_used": [],
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
    """Backward-compatible entry point; intentionally does not call any model API."""
    del client, use_web_search, use_multi_agent
    return LocalAIEngine().reply(
        request=user_request,
        history=history,
        memories=memories,
        document_context=document_context,
    )
