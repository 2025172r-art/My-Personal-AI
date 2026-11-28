"""Exact, bounded matrix and vector tools for the local My Personal AI engine.

Inputs are parsed with ast.literal_eval, never eval/exec. Fractions keep
integer and terminating-decimal calculations exact wherever possible.
"""
from __future__ import annotations

import ast
import math
from fractions import Fraction
from typing import Any

MAX_DIMENSION = 4
MAX_ABS_INPUT = 1_000_000


def _extract_arrays(text: str) -> list[Any]:
    """Extract top-level [...] literals while respecting nested brackets."""
    if not text or len(text) > 700:
        return []
    found: list[Any] = []
    index = 0
    while index < len(text):
        if text[index] != "[":
            index += 1
            continue
        start = index
        depth = 0
        quote: str | None = None
        escaped = False
        end = None
        for cursor in range(index, len(text)):
            char = text[cursor]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in {"'", '"'}:
                quote = char
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    end = cursor + 1
                    break
        if end is None:
            break
        literal = text[start:end]
        try:
            value = ast.literal_eval(literal)
        except (SyntaxError, ValueError, TypeError, MemoryError, RecursionError):
            index = end
            continue
        if isinstance(value, list):
            found.append(value)
        index = end
    return found[:2]


def _to_fraction(value: Any) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("行列の要素は整数または小数にしてください。")
    if not math.isfinite(float(value)) or abs(float(value)) > MAX_ABS_INPUT:
        raise ValueError("入力できる数値は絶対値1,000,000以下です。")
    return Fraction(str(value))


def _as_matrix(value: Any) -> list[list[Fraction]]:
    if not isinstance(value, list) or not value or len(value) > MAX_DIMENSION:
        raise ValueError("行列は1〜4行で入力してください。")
    if any(not isinstance(row, list) or not row for row in value):
        raise ValueError("行列は [ [1, 2], [3, 4] ] の形で入力してください。")
    width = len(value[0])
    if width < 1 or width > MAX_DIMENSION or any(len(row) != width for row in value):
        raise ValueError("行列は1〜4列の長方形にしてください。")
    return [[_to_fraction(item) for item in row] for row in value]


def _as_vector(value: Any) -> list[Fraction]:
    if not isinstance(value, list) or not value or len(value) > MAX_DIMENSION:
        raise ValueError("ベクトルは1〜4個の要素で入力してください。")
    if any(isinstance(item, list) for item in value):
        raise ValueError("ベクトルは [1, 2, 3] の形で入力してください。")
    return [_to_fraction(item) for item in value]


def _fmt(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _render_matrix(matrix: list[list[Fraction]]) -> str:
    return "[\n" + "\n".join(
        "  [" + ", ".join(_fmt(value) for value in row) + "]"
        for row in matrix
    ) + "\n]"


def _rref(
    source: list[list[Fraction]],
    pivot_limit: int | None = None,
) -> tuple[list[list[Fraction]], list[int]]:
    """Return reduced row-echelon form and pivot-column indices."""
    matrix = [row[:] for row in source]
    if not matrix:
        return matrix, []
    column_count = len(matrix[0])
    limit = column_count if pivot_limit is None else min(pivot_limit, column_count)
    pivot_columns: list[int] = []
    pivot_row = 0

    for column in range(limit):
        selected = next(
            (row for row in range(pivot_row, len(matrix)) if matrix[row][column] != 0),
            None,
        )
        if selected is None:
            continue
        matrix[pivot_row], matrix[selected] = matrix[selected], matrix[pivot_row]
        pivot = matrix[pivot_row][column]
        matrix[pivot_row] = [value / pivot for value in matrix[pivot_row]]

        for row in range(len(matrix)):
            if row == pivot_row:
                continue
            factor = matrix[row][column]
            if factor:
                matrix[row] = [
                    matrix[row][col] - factor * matrix[pivot_row][col]
                    for col in range(column_count)
                ]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    return matrix, pivot_columns


def _determinant(matrix: list[list[Fraction]]) -> Fraction:
    size = len(matrix)
    if any(len(row) != size for row in matrix):
        raise ValueError("行列式は正方行列で計算します。")
    work = [row[:] for row in matrix]
    determinant = Fraction(1)
    for column in range(size):
        selected = next(
            (row for row in range(column, size) if work[row][column] != 0),
            None,
        )
        if selected is None:
            return Fraction(0)
        if selected != column:
            work[column], work[selected] = work[selected], work[column]
            determinant *= -1
        pivot = work[column][column]
        determinant *= pivot
        for row in range(column + 1, size):
            factor = work[row][column] / pivot
            for col in range(column + 1, size):
                work[row][col] -= factor * work[column][col]
            work[row][column] = Fraction(0)
    return determinant


def _inverse(matrix: list[list[Fraction]]) -> list[list[Fraction]]:
    size = len(matrix)
    if any(len(row) != size for row in matrix):
        raise ValueError("逆行列は正方行列で計算します。")
    augmented = [
        row[:] + [Fraction(int(row_index == col)) for col in range(size)]
        for row_index, row in enumerate(matrix)
    ]
    reduced, pivots = _rref(augmented, pivot_limit=size)
    if pivots != list(range(size)):
        raise ValueError("この行列は正則ではないため、逆行列がありません。")
    inverse = [row[size:] for row in reduced]
    # Verify A × A⁻¹ = I exactly before returning the result.
    for row in range(size):
        for col in range(size):
            value = sum(
                (matrix[row][k] * inverse[k][col] for k in range(size)),
                Fraction(0),
            )
            if value != Fraction(int(row == col)):
                raise ValueError("逆行列の検算に失敗しました。")
    return inverse


def _solve_augmented(matrix: list[list[Fraction]]) -> str:
    variable_count = len(matrix[0]) - 1
    if variable_count < 1 or variable_count > MAX_DIMENSION:
        raise ValueError("未知数は1〜4個にしてください。")
    reduced, pivots = _rref(matrix, pivot_limit=variable_count)

    for row in reduced:
        if all(value == 0 for value in row[:variable_count]) and row[-1] != 0:
            return "**連立一次方程式**\n掃き出し法の結果、すべての式を同時に満たす解はありません。"

    rank = len(pivots)
    if rank < variable_count:
        labels = ["x", "y", "z", "w"]
        free_columns = [col for col in range(variable_count) if col not in pivots]
        free_names = [labels[col] for col in free_columns]
        lines = [
            "**連立一次方程式（掃き出し法）**",
            f"係数行列の階数は {rank}、未知数は {variable_count} 個です。",
            "自由変数があるため、解は一つに定まりません。",
            "自由変数：" + "、".join(free_names),
        ]
        return "\n".join(lines)

    labels = ["x", "y", "z", "w"]
    solution = [Fraction(0) for _ in range(variable_count)]
    for row_index, pivot_column in enumerate(pivots):
        solution[pivot_column] = reduced[row_index][-1]

    # Substitute the exact solution into every original equation.
    for row in matrix:
        left = sum(
            (row[col] * solution[col] for col in range(variable_count)),
            Fraction(0),
        )
        if left != row[-1]:
            raise ValueError("解を元の式に代入した検算に失敗しました。")

    values = "、".join(
        f"{labels[index]} = {_fmt(value)}"
        for index, value in enumerate(solution)
    )
    checks = "\n".join(
        f"第{index + 1}式：左辺 = {_fmt(sum((row[col] * solution[col] for col in range(variable_count)), Fraction(0)))}、右辺 = {_fmt(row[-1])}"
        for index, row in enumerate(matrix)
    )
    return (
        "**連立一次方程式（掃き出し法）**\n"
        f"答え：{values}\n"
        "検算：すべての式に解を代入し、一致することを確認しました。\n"
        + checks
    )


def solve_linear_algebra(request: str) -> str | None:
    """Solve explicitly requested small matrix/vector tasks without external APIs."""
    text = (request or "").strip()
    if not text or len(text) > 700:
        return None
    arrays = _extract_arrays(text)
    if not arrays:
        return None

    try:
        is_matrix = [bool(value) and isinstance(value[0], list) for value in arrays]
        if all(is_matrix):
            matrices = [_as_matrix(value) for value in arrays]
            if len(matrices) == 1:
                matrix = matrices[0]
                if any(cue in text for cue in ("掃き出し法", "拡大係数", "連立方程式", "連立一次")):
                    if len(matrix[0]) < 2:
                        raise ValueError("拡大係数行列には未知数列と右辺列が必要です。")
                    return _solve_augmented(matrix)
                if any(cue in text for cue in ("行列式", "determinant", "det")):
                    value = _determinant(matrix)
                    return f"**行列式**\ndet(A) = {_fmt(value)}"
                if any(cue in text for cue in ("逆行列", "inverse")):
                    inverse = _inverse(matrix)
                    return (
                        "**逆行列**\n"
                        f"A⁻¹ = {_render_matrix(inverse)}\n"
                        "検算：A × A⁻¹ = 単位行列になることを確認しました。"
                    )
                if any(cue in text for cue in ("転置", "transpose")):
                    transposed = [list(row) for row in zip(*matrix)]
                    return f"**転置行列**\nAᵀ = {_render_matrix(transposed)}"
                if any(cue in text for cue in ("トレース", "対角成分の和", "trace")):
                    if len(matrix) != len(matrix[0]):
                        raise ValueError("トレースは正方行列で計算します。")
                    value = sum((matrix[i][i] for i in range(len(matrix))), Fraction(0))
                    return f"**トレース**\ntr(A) = {_fmt(value)}"
                if any(cue in text for cue in ("階数", "ランク", "rank")):
                    _, pivots = _rref(matrix)
                    return f"**行列の階数**\nrank(A) = {len(pivots)}"
                return None

            left, right = matrices
            if any(cue in text for cue in ("積", "掛け", "乗算", "multiply", "×", "*")):
                if len(left[0]) != len(right):
                    raise ValueError("左の列数と右の行数が一致しないため、積を計算できません。")
                product = [
                    [
                        sum((left[row][k] * right[k][col] for k in range(len(right))), Fraction(0))
                        for col in range(len(right[0]))
                    ]
                    for row in range(len(left))
                ]
                # Exact multiplication check via direct recomputation.
                return f"**行列の積**\nA × B = {_render_matrix(product)}\n検算：各要素を行と列の内積で再計算しました。"
            if any(cue in text for cue in ("差", "引き", "減算", "subtract", "−")) or re.search(r"\]\s*-\s*\[", text):
                if len(left) != len(right) or len(left[0]) != len(right[0]):
                    raise ValueError("加減算には同じサイズの行列が必要です。")
                result = [
                    [left[row][col] - right[row][col] for col in range(len(left[0]))]
                    for row in range(len(left))
                ]
                return f"**行列の差**\nA − B = {_render_matrix(result)}"
            if any(cue in text for cue in ("和", "足し", "加算", "add", "+")) or re.search(r"\]\s*\+\s*\[", text):
                if len(left) != len(right) or len(left[0]) != len(right[0]):
                    raise ValueError("加減算には同じサイズの行列が必要です。")
                result = [
                    [left[row][col] + right[row][col] for col in range(len(left[0]))]
                    for row in range(len(left))
                ]
                return f"**行列の和**\nA + B = {_render_matrix(result)}"
            return None

        if not any(is_matrix):
            vectors = [_as_vector(value) for value in arrays]
            if len(vectors) == 2 and any(cue in text for cue in ("内積", "dot")):
                if len(vectors[0]) != len(vectors[1]):
                    raise ValueError("内積を求めるにはベクトルの次元をそろえてください。")
                value = sum(
                    (vectors[0][index] * vectors[1][index] for index in range(len(vectors[0]))),
                    Fraction(0),
                )
                return f"**ベクトルの内積**\na・b = {_fmt(value)}"
            if len(vectors) == 2 and any(cue in text for cue in ("外積", "cross")):
                if len(vectors[0]) != 3 or len(vectors[1]) != 3:
                    raise ValueError("外積は3次元ベクトルで計算します。")
                a, b = vectors
                value = [
                    a[1] * b[2] - a[2] * b[1],
                    a[2] * b[0] - a[0] * b[2],
                    a[0] * b[1] - a[1] * b[0],
                ]
                return "**ベクトルの外積**\na × b = [" + ", ".join(_fmt(item) for item in value) + "]"
            if len(vectors) == 1 and any(cue in text for cue in ("大きさ", "ノルム", "magnitude")):
                squared = sum((value * value for value in vectors[0]), Fraction(0))
                magnitude = math.sqrt(float(squared))
                return f"**ベクトルの大きさ**\n|a| = √({_fmt(squared)}) ≈ {magnitude:.8g}"
        return None
    except ValueError as exc:
        return str(exc)
    except (TypeError, ZeroDivisionError, OverflowError, SyntaxError):
        return "この行列・ベクトルの入力は対応範囲外です。1〜4次元の数値配列を使ってください。"
