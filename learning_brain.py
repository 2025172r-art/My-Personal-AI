"""Small, locally trained intent model for My Personal AI.

This is a transparent Multinomial Naive Bayes classifier, not a generative
language model. It trains from bundled examples plus optional user-labelled
examples stored in the app's own long-term memory.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Iterable

INTENT_LABELS = {
    "calculation",
    "factual_question",
    "planning",
    "coding",
    "summarization",
    "creative",
    "conversation",
    "current_information",
}

LABEL_ALIASES = {
    "計算": "calculation",
    "計算問題": "calculation",
    "事実質問": "factual_question",
    "知識": "factual_question",
    "説明": "factual_question",
    "計画": "planning",
    "予定": "planning",
    "プログラミング": "coding",
    "コード": "coding",
    "要約": "summarization",
    "まとめ": "summarization",
    "創作": "creative",
    "物語": "creative",
    "会話": "conversation",
    "雑談": "conversation",
    "最新情報": "current_information",
    "時事": "current_information",
}


def tokenize(text: str) -> list[str]:
    """Create word and character-ngram features for Japanese and English text."""
    features: list[str] = []
    for piece in re.findall(r"[a-z0-9_]+|[ぁ-んァ-ン一-龥]+", (text or "").lower()):
        if re.fullmatch(r"[a-z0-9_]+", piece):
            features.append("w:" + piece)
            continue
        if len(piece) == 1:
            features.append("c:" + piece)
            continue
        for width in (2, 3):
            if len(piece) >= width:
                features.extend(
                    "c:" + piece[index:index + width]
                    for index in range(len(piece) - width + 1)
                )
    return features


class MultinomialNaiveBayes:
    """A minimal incremental Multinomial Naive Bayes text classifier."""

    def __init__(self, alpha: float = 1.0) -> None:
        if not math.isfinite(alpha) or alpha <= 0:
            raise ValueError("alpha must be a positive finite number")
        self.alpha = alpha
        self.document_counts: Counter[str] = Counter()
        self.token_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self.total_tokens: Counter[str] = Counter()
        self.vocabulary: set[str] = set()

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(sorted(self.document_counts))

    def fit(self, examples: Iterable[tuple[str, str]]) -> "MultinomialNaiveBayes":
        self.document_counts.clear()
        self.token_counts.clear()
        self.total_tokens.clear()
        self.vocabulary.clear()
        return self.partial_fit(examples)

    def partial_fit(
        self,
        examples: Iterable[tuple[str, str]],
    ) -> "MultinomialNaiveBayes":
        for text, label in examples:
            label = str(label).strip()
            tokens = tokenize(str(text))
            if label not in INTENT_LABELS or not tokens:
                continue
            counts = Counter(tokens)
            self.document_counts[label] += 1
            self.token_counts[label].update(counts)
            self.total_tokens[label] += sum(counts.values())
            self.vocabulary.update(counts)
        return self

    def predict(self, text: str) -> dict[str, object]:
        tokens = tokenize(text)
        if not tokens or not self.document_counts:
            return {
                "label": "unknown",
                "confidence": 0.0,
                "margin": 0.0,
                "scores": {},
            }

        total_documents = sum(self.document_counts.values())
        vocabulary_size = max(1, len(self.vocabulary))
        log_scores: dict[str, float] = {}
        for label in self.labels:
            log_score = math.log(
                (self.document_counts[label] + self.alpha)
                / (total_documents + self.alpha * len(self.document_counts))
            )
            denominator = self.total_tokens[label] + self.alpha * vocabulary_size
            token_table = self.token_counts[label]
            for token, count in Counter(tokens).items():
                probability = (token_table[token] + self.alpha) / denominator
                log_score += count * math.log(probability)
            log_scores[label] = log_score

        max_score = max(log_scores.values())
        exponentials = {
            label: math.exp(score - max_score)
            for label, score in log_scores.items()
        }
        normalizer = sum(exponentials.values()) or 1.0
        probabilities = {
            label: value / normalizer
            for label, value in exponentials.items()
        }
        ranked = sorted(
            probabilities.items(),
            key=lambda item: (-item[1], item[0]),
        )
        confidence = ranked[0][1]
        runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
        return {
            "label": ranked[0][0],
            "confidence": confidence,
            "margin": confidence - runner_up,
            "scores": probabilities,
        }


DEFAULT_TRAINING_EXAMPLES: list[tuple[str, str]] = [
    ("2+3を計算して", "calculation"),
    ("125かける8はいくつ", "calculation"),
    ("平均値と中央値を求めて", "calculation"),
    ("400円の20パーセント引き", "calculation"),
    ("二次方程式を解いて", "calculation"),
    ("この公式で答えを出して", "calculation"),
    ("光合成とは何ですか", "factual_question"),
    ("電磁誘導の仕組みを説明して", "factual_question"),
    ("DNAの役割を教えて", "factual_question"),
    ("HTTPとHTTPSの違いは", "factual_question"),
    ("なぜ空は青く見えるの", "factual_question"),
    ("重力の意味を知りたい", "factual_question"),
    ("来週の勉強計画を作って", "planning"),
    ("このアプリの開発手順を考えて", "planning"),
    ("発表までのスケジュールを立てて", "planning"),
    ("やることを順番に整理して", "planning"),
    ("試験勉強の予定を作成", "planning"),
    ("プロジェクトの段取りを決めたい", "planning"),
    ("Pythonで関数を書くコードを作って", "coding"),
    ("このエラーをデバッグして", "coding"),
    ("HTMLとCSSのページを実装したい", "coding"),
    ("SQLのクエリを書いて", "coding"),
    ("プログラムのバグを直したい", "coding"),
    ("Pythonのテストを追加する", "coding"),
    ("このPDFの内容を短く要約して", "summarization"),
    ("文章の要点を抜き出して", "summarization"),
    ("このレポートをまとめて", "summarization"),
    ("長い資料を要約して", "summarization"),
    ("ファイルの重要な部分を整理して", "summarization"),
    ("議事録を短くまとめる", "summarization"),
    ("冒険の物語を書いて", "creative"),
    ("詩を作ってください", "creative"),
    ("新しいゲームのアイデアを考えて", "creative"),
    ("架空の世界を設定して", "creative"),
    ("面白いキャラクターを考えて", "creative"),
    ("短い小説の設定を作る", "creative"),
    ("こんにちは", "conversation"),
    ("今日は元気ですか", "conversation"),
    ("少し雑談しよう", "conversation"),
    ("ありがとう", "conversation"),
    ("どう思いますか", "conversation"),
    ("好きな勉強方法は何", "conversation"),
    ("今日の天気を教えて", "current_information"),
    ("現在の株価はいくら", "current_information"),
    ("最新ニュースを知りたい", "current_information"),
    ("今の為替レートを確認", "current_information"),
    ("今週のイベント情報を探して", "current_information"),
    ("現在のソフトウェア最新版は", "current_information"),
]


def examples_from_memories(
    memories: Iterable[dict[str, object]] | None,
) -> list[tuple[str, str]]:
    """Read opt-in examples stored as category 'AI学習例'.

    Each memory content must use: label | example text
    Accepted labels are the English labels above or LABEL_ALIASES.
    """
    examples: list[tuple[str, str]] = []
    for memory in memories or []:
        if memory.get("category") != "AI学習例":
            continue
        content = str(memory.get("content", "")).strip()
        if "|" not in content:
            continue
        raw_label, sample = (part.strip() for part in content.split("|", 1))
        label = LABEL_ALIASES.get(raw_label, raw_label)
        if label in INTENT_LABELS and 2 <= len(sample) <= 240:
            examples.append((sample, label))
    return examples


def train_default_classifier(
    memories: Iterable[dict[str, object]] | None = None,
) -> MultinomialNaiveBayes:
    """Train from bundled samples and optional user-labelled long-term memories."""
    classifier = MultinomialNaiveBayes()
    classifier.fit(DEFAULT_TRAINING_EXAMPLES)
    return classifier.partial_fit(examples_from_memories(memories))
