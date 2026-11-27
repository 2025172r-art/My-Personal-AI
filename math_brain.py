"""Bounded school-level mathematics and chemistry reasoning tools."""
from __future__ import annotations

import ast
import math
import re
from collections import Counter
from typing import Any

LINEAR_BINARY_OPERATORS = (ast.Add, ast.Sub, ast.Mult, ast.Div)


def _linear_coefficients(node: ast.AST, depth: int = 0) -> tuple[float, float, float]:
    """Parse a linear expression into (constant, x coefficient, y coefficient)."""
    if depth > 20:
        raise ValueError("expression too deeply nested")
    if isinstance(node, ast.Expression):
        return _linear_coefficients(node.body, depth + 1)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        value = float(node.value)
        if not math.isfinite(value) or abs(value) > 10**9:
            raise ValueError("number outside supported range")
        return value, 0.0, 0.0
    if isinstance(node, ast.Name) and node.id.lower() in {"x", "y"}:
        return (0.0, 1.0, 0.0) if node.id.lower() == "x" else (0.0, 0.0, 1.0)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        c, x, y = _linear_coefficients(node.operand, depth + 1)
        sign = -1.0 if isinstance(node.op, ast.USub) else 1.0
        return sign * c, sign * x, sign * y
    if isinstance(node, ast.BinOp):
        left = _linear_coefficients(node.left, depth + 1)
        right = _linear_coefficients(node.right, depth + 1)
        if isinstance(node.op, ast.Add):
            return tuple(left[i] + right[i] for i in range(3))
        if isinstance(node.op, ast.Sub):
            return tuple(left[i] - right[i] for i in range(3))
        if isinstance(node.op, ast.Mult):
            left_is_constant = abs(left[1]) < 1e-12 and abs(left[2]) < 1e-12
            right_is_constant = abs(right[1]) < 1e-12 and abs(right[2]) < 1e-12
            if left_is_constant:
                return tuple(left[0] * value for value in right)
            if right_is_constant:
                return tuple(right[0] * value for value in left)
            raise ValueError("non-linear term")
        if isinstance(node.op, ast.Div):
            if abs(right[1]) > 1e-12 or abs(right[2]) > 1e-12 or abs(right[0]) < 1e-12:
                raise ValueError("division must be by a nonzero constant")
            return tuple(value / right[0] for value in left)
    raise ValueError("unsupported expression")


def _normalise_linear_equation(equation: str) -> tuple[float, float, float]:
    text = equation.strip().lower().replace("＝", "=").replace("−", "-").replace("×", "*")
    text = re.sub(r"(?<=\d)\s*(?=[xy]\b|\()", "*", text)
    text = re.sub(r"(?<=\))\s*(?=[xy]\b|\()", "*", text)
    text = re.sub(r"(?<=[xy])\s*(?=\()", "*", text)
    if text.count("=") != 1:
        raise ValueError("one equals sign required")
    left_text, right_text = (part.strip() for part in text.split("=", 1))
    left_tree = ast.parse(left_text, mode="eval")
    right_tree = ast.parse(right_text, mode="eval")
    if sum(1 for _ in ast.walk(left_tree)) + sum(1 for _ in ast.walk(right_tree)) > 60:
        raise ValueError("equation too complex")
    left = _linear_coefficients(left_tree)
    right = _linear_coefficients(right_tree)
    return tuple(left[index] - right[index] for index in range(3))


def solve_linear_system(request: str) -> str | None:
    """Solve two simultaneous linear equations in x and y."""
    text = (request or "").strip()
    text = re.sub(r"^(?:連立一次方程式|連立方程式|連立)\s*", "", text)
    if not re.search(r"[xy]", text, re.IGNORECASE):
        return None
    if any(word in text for word in ("連立方程式", "連立", "xとy", "x、y")):
        pass
    elif text.count("=") < 2:
        return None

    equations = [part.strip() for part in re.split(r"[,;\n、]+", text) if "=" in part]
    if len(equations) != 2:
        return None
    try:
        c1, a1, b1 = _normalise_linear_equation(equations[0])
        c2, a2, b2 = _normalise_linear_equation(equations[1])
    except (SyntaxError, ValueError, TypeError, OverflowError):
        return None

    determinant = a1 * b2 - a2 * b1
    if abs(determinant) < 1e-12:
        if abs(c1 * a2 - c2 * a1) < 1e-9 and abs(c1 * b2 - c2 * b1) < 1e-9:
            return "二つの式は独立ではないため、解が一つに定まりません。"
        return "二つの式を同時に満たす解はありません。"

    rhs1, rhs2 = -c1, -c2
    x_value = (rhs1 * b2 - rhs2 * b1) / determinant
    y_value = (a1 * rhs2 - a2 * rhs1) / determinant
    if not all(math.isfinite(value) and abs(value) <= 10**12 for value in (x_value, y_value)):
        return "解が大きすぎるため表示できません。"

    residual1 = a1 * x_value + b1 * y_value + c1
    residual2 = a2 * x_value + b2 * y_value + c2
    if max(abs(residual1), abs(residual2)) > 1e-7:
        return None

    def fmt(value: float) -> str:
        return str(int(round(value))) if abs(value - round(value)) < 1e-10 else f"{value:.8g}"

    return (
        "**連立一次方程式の解**\n"
        "消去法と行列式を使ってx、yを求め、二つの式に代入して検算しました。\n"
        f"答え：x = {fmt(x_value)}、y = {fmt(y_value)}\n"
        f"検算：第1式の左辺 = {fmt(a1*x_value+b1*y_value)}、"
        f"第2式の左辺 = {fmt(a2*x_value+b2*y_value)}"
    )


def solve_number_theory(request: str) -> str | None:
    """Compute GCD, LCM, or prime factorisation for bounded positive integers."""
    text = (request or "").replace("，", ",")
    numbers = [int(value) for value in re.findall(r"(?<![A-Za-z])\d+", text)]
    if "素因数分解" in text or "素因数" in text:
        if not numbers:
            return None
        number = numbers[-1]
        if number < 2:
            return "素因数分解できるのは2以上の整数です。"
        if number > 10**12:
            return "計算できる整数は10^12以下です。"
        remaining = number
        factors: list[tuple[int, int]] = []
        divisor = 2
        while divisor * divisor <= remaining:
            if remaining % divisor == 0:
                exponent = 0
                while remaining % divisor == 0:
                    remaining //= divisor
                    exponent += 1
                factors.append((divisor, exponent))
            divisor = 3 if divisor == 2 else divisor + 2
        if remaining > 1:
            factors.append((remaining, 1))
        expression = " × ".join(
            f"{prime}^{power}" if power > 1 else str(prime)
            for prime, power in factors
        )
        return f"**素因数分解**\n{number} = {expression}"

    if len(numbers) < 2 or len(numbers) > 20:
        return None
    if any(number <= 0 or number > 10**12 for number in numbers):
        return "正の整数（1以上10^12以下）で計算してください。"

    if "最大公約数" in text or re.search(r"\bGCD\b", text, re.IGNORECASE):
        result = math.gcd(*numbers)
        return f"**最大公約数**\n{', '.join(map(str, numbers))} の最大公約数 = {result}"
    if "最小公倍数" in text or re.search(r"\bLCM\b", text, re.IGNORECASE):
        result = math.lcm(*numbers)
        if result > 10**18:
            return "最小公倍数が大きすぎるため表示できません。"
        return f"**最小公倍数**\n{', '.join(map(str, numbers))} の最小公倍数 = {result}"
    return None


ATOMIC_MASSES = {
    "H": 1.008, "He": 4.0026, "Li": 6.94, "Be": 9.0122, "B": 10.81,
    "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998, "Ne": 20.180,
    "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.085, "P": 30.974,
    "S": 32.06, "Cl": 35.45, "Ar": 39.948, "K": 39.098, "Ca": 40.078,
    "Cr": 51.996, "Mn": 54.938, "Fe": 55.845, "Co": 58.933, "Ni": 58.693,
    "Cu": 63.546, "Zn": 65.38, "Br": 79.904, "Ag": 107.868, "I": 126.904,
    "Ba": 137.327, "Au": 196.967, "Hg": 200.592, "Pb": 207.2,
}


def parse_chemical_formula(formula: str) -> dict[str, int] | None:
    """Parse element symbols, integer subscripts, and nested parentheses."""
    if not formula or len(formula) > 60:
        return None
    tokens = re.findall(r"[A-Z][a-z]?|\d+|[()]", formula)
    if "".join(tokens) != formula:
        return None
    if not tokens:
        return None

    def parse_group(index: int, nested: bool = False) -> tuple[Counter[str], int]:
        counts: Counter[str] = Counter()
        while index < len(tokens):
            token = tokens[index]
            if token == ")":
                if not nested:
                    raise ValueError("unexpected closing parenthesis")
                return counts, index + 1
            if token == "(":
                group_counts, index = parse_group(index + 1, nested=True)
                multiplier = 1
                if index < len(tokens) and tokens[index].isdigit():
                    multiplier = int(tokens[index])
                    index += 1
                if multiplier < 1 or multiplier > 1000:
                    raise ValueError("multiplier out of range")
                for element, count in group_counts.items():
                    counts[element] += count * multiplier
                continue
            if token.isdigit():
                raise ValueError("subscript must follow an element or group")
            if token not in ATOMIC_MASSES:
                raise ValueError("unknown element")
            index += 1
            multiplier = 1
            if index < len(tokens) and tokens[index].isdigit():
                multiplier = int(tokens[index])
                index += 1
            if multiplier < 1 or multiplier > 1000:
                raise ValueError("subscript out of range")
            counts[token] += multiplier
        if nested:
            raise ValueError("unclosed parenthesis")
        return counts, index

    try:
        elements, end_index = parse_group(0)
    except ValueError:
        return None
    if end_index != len(tokens) or not elements:
        return None
    return dict(elements)


def solve_molar_mass(request: str) -> str | None:
    """Calculate molar mass for common element formulae such as H2O and Ca(OH)2."""
    text = request or ""
    if not any(cue in text for cue in ("モル質量", "分子量", "式量", "g/mol")):
        return None
    match = re.search(r"(?<![A-Za-z])([A-Z][A-Za-z0-9()]{0,58})(?![A-Za-z])", text)
    if not match:
        return None
    formula = match.group(1)
    elements = parse_chemical_formula(formula)
    if elements is None:
        return None
    total_mass = sum(ATOMIC_MASSES[element] * count for element, count in elements.items())
    if not math.isfinite(total_mass) or total_mass > 10**6:
        return None
    composition = "、".join(f"{element}:{count}" for element, count in sorted(elements.items()))
    return (
        f"**{formula}のモル質量**\n"
        f"元素の数：{composition}\n"
        f"計算：{ ' + '.join(f'{ATOMIC_MASSES[e]:g}×{count}' for e, count in sorted(elements.items())) }\n"
        f"答え：約{total_mass:.4g} g/mol"
    )
