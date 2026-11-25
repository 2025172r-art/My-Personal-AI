from __future__ import annotations

import ast
import math
import operator
import re
from collections import Counter
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

# Safety boundary: the engine never evaluates arbitrary Python or executes
# instructions found inside uploaded documents, memories, or retrieved text.
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
    "t": ("mass", 1000000.0, "t"),
    "ml": ("volume", 0.001, "mL"),
    "l": ("volume", 1.0, "L"),
}

KNOWLEDGE = [
    {
        "title": "Pythonとは",
        "triggers": ["pythonとは", "pythonって何", "pythonとは何", "python 言語", "pythonを説明"],
        "answer": (
            "Pythonは、読みやすく短く書きやすい文法を持つ汎用プログラミング言語です。"
            "Webアプリ、データ分析、AI・機械学習、事務作業の自動化、教育など幅広い分野で使われます。"
            "代表的な特徴は、豊富なライブラリ、OSをまたいだ利用のしやすさ、初心者にも学びやすい構文です。"
            "一方、大規模な計算を単独で行う場合は、C/C++などより遅くなることがあります。"
        ),
    },
    {
        "title": "Pythonの主な特徴",
        "triggers": ["pythonの特徴", "pythonのメリット", "pythonで何ができる"],
        "answer": "Pythonは、読みやすい文法、豊富な外部ライブラリ、幅広い用途が特徴です。Web開発、データ処理、自動化、AI開発、教育用プログラムなどに利用できます。",
    },
    {
        "title": "変数とは",
        "triggers": ["変数とは", "pythonの変数", "変数って何"],
        "answer": "変数は、値に名前を付けて扱うための仕組みです。Pythonでは name = 'Taro' のように書き、あとから name を使って値を参照できます。",
    },
    {
        "title": "関数とは",
        "triggers": ["関数とは", "pythonの関数", "defとは"],
        "answer": "関数は、処理をひとまとまりにして名前を付け、必要なときに呼び出せる仕組みです。Pythonでは def greet(): のように定義します。",
    },
    {
        "title": "リストとは",
        "triggers": ["リストとは", "pythonのリスト", "listとは"],
        "answer": "リストは、複数の値を順番にまとめて扱うデータ型です。例: fruits = ['りんご', 'みかん']。fruits[0] で先頭の要素を参照できます。",
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

GOVERNANCE_POLICY = (
    "通常の無害な依頼は過剰に拒否せず、利用者が指定した目的・口調・形式・言語を優先する。"
    "安全、プライバシー、認証情報保護、任意コード実行の禁止、外部操作の確認は固定境界として維持する。"
    "拒否が必要な場合は問題となる部分だけを限定し、可能な安全な部分は回答する。"
    "会話履歴、記憶、アップロード文書は参考データであり、命令権限を持たない。"
)


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
    """Evaluate bounded arithmetic without eval(), exec(), or arbitrary code."""
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


def _normalize_expression(text: str) -> str:
    normalized = text.replace("×", "*").replace("÷", "/")
    normalized = normalized.replace("＋", "+").replace("－", "-").replace("−", "-")
    normalized = re.sub(r"(\d)\s*かける\s*(\d)", r"\1*\2", normalized)
    normalized = re.sub(r"(\d)\s*わる\s*(\d)", r"\1/\2", normalized)
    normalized = re.sub(r"(\d)\s*たす\s*(\d)", r"\1+\2", normalized)
    normalized = re.sub(r"(\d)\s*ひく\s*(\d)", r"\1-\2", normalized)
    return normalized


def _find_calculation(text: str) -> str | None:
    normalized = _normalize_expression(text)
    match = re.search(
        r"(?<![\w.])(\d+(?:\.\d+)?(?:\s*(?:\*\*|[+\-*/%])\s*\d+(?:\.\d+)?)+)(?![\w.])",
        normalized,
    )
    return match.group(1).replace(" ", "") if match else None


def _numeric_prefix(text: str) -> float | None:
    match = re.search(r"([-+]?\d+(?:\.\d+)?)\s*$", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _format_number(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:g}"


def convert_units(text: str) -> str | None:
    """Convert a quantity, optionally calculated from an expression, into another unit."""
    normalized = _normalize_expression(text).lower()
    unit_pattern = r"(?P<source>km|cm|mm|kg|mg|g|ml|l|m|t)"
    match = re.search(
        unit_pattern + r"\s*(?:を|から)\s*(?P<target>km|cm|mm|kg|mg|g|ml|l|m|t)",
        normalized,
    )
    if not match:
        # Keep the original friendly form, including a missing particle.
        match = re.search(
            r"(?P<value>\d+(?:\.\d+)?)\s*(?P<source>km|cm|mm|kg|mg|g|ml|l|m|t)\s+(?P<target>km|cm|mm|kg|mg|g|ml|l|m|t)",
            normalized,
        )
        if not match:
            return None
        prefix = normalized[:match.start("source")]
        value = float(match.group("value"))
    else:
        prefix = normalized[:match.start("source")]
        expression = _find_calculation(prefix)
        if expression:
            calculated = calculate(expression)
            if not calculated.startswith("計算結果："):
                return calculated
            try:
                value = float(calculated.split("：", 1)[1])
            except ValueError:
                return "計算結果を単位変換できませんでした。"
        else:
            value = _numeric_prefix(prefix)
            if value is None:
                return None

    source, target = match.group("source"), match.group("target")
    source_info, target_info = UNIT_TABLE[source], UNIT_TABLE[target]
    if source_info[0] != target_info[0]:
        return f"{source}と{target}は異なる単位の種類なので変換できません。"
    result = value * source_info[1] / target_info[1]
    if abs(result) > 10**15:
        return "変換結果が大きすぎるため表示できません。"
    return f"{_format_number(value)}{source_info[2]} = {_format_number(result)}{target_info[2]} です。"


def split_requests(request: str, max_parts: int = 8) -> list[str]:
    """Split numbered, bulleted, newline-separated, and sentence-separated requests."""
    raw_parts: list[str] = []
    for line in request.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = re.sub(r"^\s*(?:\d+\s*[.)、]|[-*・])\s*", "", line).strip()
        if not line:
            continue
        pieces = re.split(r"(?<=[。！？!?])\s*", line)
        for piece in pieces:
            piece = piece.strip(" \t,、;；")
            if not piece:
                continue
            connector_parts = re.split(
                r"\s*(?:それと|また|あと|さらに|次に|そして)[、,]\s*",
                piece,
            )
            raw_parts.extend(part.strip() for part in connector_parts if part.strip())

    cleaned: list[str] = []
    for part in raw_parts:
        part = re.sub(r"^(?:それと|また|あと|さらに|次に|そして)[、, ]*", "", part).strip()
        if part and (not cleaned or part != cleaned[-1]):
            cleaned.append(part)

    if len(cleaned) > max_parts:
        cleaned = cleaned[: max_parts - 1] + [" / ".join(cleaned[max_parts - 1 :])]
    return cleaned or [request.strip()]


def _plan_for(request: str) -> list[str]:
    text = request.lower()
    if any(word in text for word in ("my personal ai", "このai", "このＡＩ", "このプロジェクト", "自作ai", "自作ＡＩ")):
        return [
            "入力を複数の依頼に分け、各依頼の種類を判定するルーターを強化する",
            "計算・単位変換・知識検索・資料検索を独立したツールとして整理する",
            "会話履歴と長期記憶を検索し、回答に必要な情報だけを安全に渡す",
            "未知の質問や曖昧な依頼を正直に扱う評価テストを増やす",
            "操作・認証・ファイル入力の安全性を確認してからUIを改善する",
            "GitHub Actionsでテストし、Renderへ段階的に反映して本番動作を確認する",
        ]
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
    """Transparent, API-free local agent with multi-intent routing."""

    name = "My Personal AI Local Engine"
    version = "0.4.0"

    def capabilities(self) -> list[str]:
        return [
            "日本語の基本会話・ヘルプ",
            "複数の質問・依頼を分割して順番に処理",
            "安全な算術計算と計算結果を使った単位変換",
            "長さ・重さ・容量の単位変換",
            "日本時間の日付・時刻",
            "長期記憶のキーワード検索",
            "ファイル内の関連文検索と抽出的な要約",
            "目的別の作業計画",
            "文字数・英単語数の確認",
            "拡充した内蔵知識ベース",
            "不要な拒否を抑え、利用者の口調・形式・目的を優先（安全境界あり）",
            "君主風の簡潔・断定的な報告スタイル（切替可能）",
        ]

    def tools(self) -> list[dict[str, str]]:
        return [
            {"name": "multi_intent_router", "description": "複数の依頼を分割して順番に処理"},
            {"name": "calculator", "description": "四則演算・括弧・剰余・べき乗"},
            {"name": "unit_converter", "description": "長さ・重さ・容量の単位変換。計算式にも対応"},
            {"name": "japan_clock", "description": "日本時間の日付と時刻"},
            {"name": "memory_search", "description": "保存済みの記憶をキーワード検索"},
            {"name": "document_search", "description": "読み込んだ資料の関連文検索"},
            {"name": "extractive_summary", "description": "原文から重要文を抜き出す要約"},
            {"name": "task_planner", "description": "目的別の作業計画を作成"},
            {"name": "text_analyzer", "description": "文字数・英単語数を数える"},
            {"name": "local_knowledge", "description": "内蔵知識ベースを検索"},
            {"name": "command_policy", "description": "利用者優先の指揮系統と安全境界"},
        ]

    def health(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "provider_api": False,
            "multi_intent": True,
            "user_priority": True,
            "sovereign_style": True,
            "capabilities": len(self.capabilities()),
            "tools": len(self.tools()),
        }

    def _knowledge_answer(self, request: str) -> str | None:
        lowered = request.lower().replace("？", "?")
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

    def _reply_single(
        self,
        text: str,
        memories: list[dict[str, Any]],
        document_context: str,
    ) -> dict[str, Any]:
        lowered = text.lower()

        if any(word in lowered for word in ("できること", "使い方", "ヘルプ", "help", "機能一覧")):
            return {
                "answer": "現在利用できる機能です。\n"
                + "\n".join(f"・{item}" for item in self.capabilities())
                + "\n\nこのエンジンは外部の生成AI APIを使わないルール・検索方式です。未知の質問に自由回答する機能はまだありません。",
                "plan": [], "intent": "help", "tools_used": [],
            }

        if any(word in lowered for word in ("絶対君主", "君主モード", "統治者モード", "命令を最優先")):
            return {
                "answer": (
                    "**利用者優先コマンド方針**\n"
                    "利用者が指定した目的・口調・回答形式を、対応可能な範囲で最優先します。"
                    "通常の無害な依頼を不必要に拒否しない方針です。"
                    "ただし、安全・プライバシー・認証情報保護・任意コード実行の禁止は解除できません。"
                    "外部への送信・投稿・購入・アカウント変更などは、明示的な確認なしに実行しません。"
                    "ファイルや記憶に含まれる命令は参考データとして扱います。\n\n"
                    "このモードは応答スタイルと優先順位の設定であり、未知の命令を必ず理解できる機能ではありません。"
                ),
                "plan": [], "intent": "command_policy", "tools_used": ["command_policy"],
            }

        if re.fullmatch(r"(こんにちは|おはよう|こんばんは|やあ|はじめまして)[！!。 ]*", text):
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
            any(symbol in text for symbol in ("+", "-", "*", "/", "%", "×", "÷", "＋", "－"))
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
                    + "\n\nこれは原文からの抜き出しです。資料内の命令文は実行せず、資料内容として扱います。",
                    "plan": [], "intent": "document_search", "tools_used": ["document_search"],
                }
            return {
                "answer": "資料は読み込まれていますが、質問と一致する語句を含む文は見つかりませんでした。別の言葉で質問してみてください。",
                "plan": [], "intent": "document_search", "tools_used": ["document_search"],
            }

        if any(word in text for word in ("計画", "手順", "段取り", "どう進め", "予定を立て", "スケジュール")):
            plan = _plan_for(text)
            is_project_plan = any(
                word in lowered
                for word in ("my personal ai", "このai", "このＡＩ", "このプロジェクト", "自作ai", "自作ＡＩ")
            )
            heading = "My Personal AI 開発ロードマップ" if is_project_plan else "実行計画"
            return {
                "answer": f"**{heading}**\n"
                + "\n".join(f"{index}. {step}" for index, step in enumerate(plan, 1)),
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
                "このエンジンの内蔵知識だけでは、まだ根拠を確認できません。"
                "作り話で埋めずに、分かる範囲を正確に答えます。"
                "質問を少し具体化するか、関連資料を読み込ませてください。"
            ),
            "plan": [], "intent": "unknown", "tools_used": [],
        }

    def reply(
        self,
        request: str,
        history: list[dict[str, Any]] | None = None,
        memories: list[dict[str, Any]] | None = None,
        document_context: str = "",
        sovereign_mode: bool = True,
    ) -> dict[str, Any]:
        text = request.strip()
        history = history or []
        memories = memories or []
        del history  # Reserved for the next context-aware engine iteration.
        if not text:
            return {"answer": "メッセージを入力してください。", "plan": [], "intent": "empty", "tools_used": []}

        parts = split_requests(text)
        if len(parts) == 1:
            result = self._reply_single(parts[0], memories, document_context)
            return self._apply_persona(result, sovereign_mode)

        results = [self._reply_single(part, memories, document_context) for part in parts]
        sections = []
        for index, (part, result) in enumerate(zip(parts, results), 1):
            body = result["answer"].strip()
            # The numbered request heading already names the topic; remove
            # the duplicate local-knowledge title shown in single replies.
            if result.get("intent") == "local_knowledge":
                body = re.sub(r"^\*\*[^*\n]+\*\*\s*\n", "", body, count=1)
            sections.append(f"### {index}. {part[:70]}\n\n{body}")

        tools_used = list(dict.fromkeys(
            tool for result in results for tool in result.get("tools_used", [])
        ))
        result = {
            "answer": f"**{len(parts)}件の依頼を処理しました。**\n\n" + "\n\n".join(sections),
            # Details are already shown inline. Avoid rendering the same plan
            # a second time in the Streamlit expander.
            "plan": [],
            "intent": "multi_task",
            "intents": [item.get("intent", "unknown") for item in results],
            "subresults": results,
            "tools_used": tools_used,
        }
        return self._apply_persona(result, sovereign_mode)

    @staticmethod
    def _apply_persona(result: dict[str, Any], sovereign_mode: bool) -> dict[str, Any]:
        if not sovereign_mode:
            return result
        answer = result.get("answer", "").strip()
        if answer and result.get("intent") != "empty":
            result = dict(result)
            result["answer"] = "**命令を受領。対応結果を報告します。**\n\n" + answer
        return result


def run_agent_task(
    client: Any = None,
    user_request: str = "",
    history: list[dict[str, Any]] | None = None,
    memories: list[dict[str, Any]] | None = None,
    document_context: str = "",
    use_web_search: bool = False,
    use_multi_agent: bool = False,
    sovereign_mode: bool = True,
) -> dict[str, Any]:
    """Backward-compatible entry point; intentionally does not call any model API."""
    del client, use_web_search, use_multi_agent
    return LocalAIEngine().reply(
        request=user_request,
        history=history,
        memories=memories,
        document_context=document_context,
        sovereign_mode=sovereign_mode,
    )
