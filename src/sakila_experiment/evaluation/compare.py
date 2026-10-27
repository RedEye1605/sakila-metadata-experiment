"""Position-preserving, duplicate-preserving result comparison.

Exact comparisons use rational numeric values, never lossy rounding. Optional
approximate columns use a complete one-to-one row matching, not greedy pairing.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction

from ..db.execute import ResultTable
from ..db.values import encode_value

COMPARATOR_VERSION = "ex-results-v1"


class EvaluationError(RuntimeError):
    """An evaluator/contract issue, not a model failure."""


@dataclass(frozen=True)
class ComparisonSpec:
    column_count: int
    ordered: bool = False
    approximate_columns: tuple[int, ...] = ()
    absolute_tolerance: str = "1e-9"
    relative_tolerance: str = "1e-12"

    def __post_init__(self):
        if self.column_count < 1:
            raise EvaluationError("Comparison requires a positive column count")
        if len(set(self.approximate_columns)) != len(self.approximate_columns) or any(i < 0 or i >= self.column_count for i in self.approximate_columns):
            raise EvaluationError("Invalid approximate-column contract")
        for value in (self.absolute_tolerance, self.relative_tolerance):
            try:
                if not Decimal(value).is_finite() or Decimal(value) < 0:
                    raise EvaluationError("Tolerances must be finite and nonnegative")
            except Exception as exc:
                raise EvaluationError("Invalid numeric tolerance") from exc


@dataclass(frozen=True)
class ComparisonResult:
    execution_accuracy: int
    reason: str


def numeric(value) -> Fraction | None:
    if isinstance(value, (int, Decimal, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise EvaluationError("Non-finite numeric result")
        if isinstance(value, Decimal) and not value.is_finite():
            raise EvaluationError("Non-finite numeric result")
        return Fraction(value)
    return None


def cell_key(value):
    number = numeric(value)
    if number is not None:
        return ("numeric", number)
    if isinstance(value, datetime) and value.tzinfo is not None:
        return ("aware_datetime", value.astimezone(timezone.utc).isoformat(timespec="microseconds"))
    try:
        return tuple(encode_value(value))
    except (TypeError, ValueError) as exc:
        raise EvaluationError("Unsupported result value") from exc


def rows_match(actual: tuple, gold: tuple, spec: ComparisonSpec) -> bool:
    approximate = set(spec.approximate_columns)
    for column, (left, right) in enumerate(zip(actual, gold, strict=True)):
        if column in approximate:
            a, b = numeric(left), numeric(right)
            if a is not None and b is not None:
                tolerance = Fraction(Decimal(spec.absolute_tolerance)) + Fraction(Decimal(spec.relative_tolerance)) * abs(b)
                if abs(a - b) > tolerance:
                    return False
                continue
        if cell_key(left) != cell_key(right):
            return False
    return True


def has_perfect_matching(actual: list[tuple], gold: list[tuple], spec: ComparisonSpec) -> bool:
    if len(actual) * len(gold) > 1000000:
        raise EvaluationError("Approximate matching exceeds the reviewed comparison budget")
    adjacency = [[index for index, reference in enumerate(gold) if rows_match(row, reference, spec)] for row in actual]
    left_matches: dict[int, int] = {}
    right_matches: dict[int, int] = {}
    for root in range(len(actual)):
        queue = deque([root])
        seen_left = {root}
        parent_right: dict[int, int] = {}
        free_right = None
        while queue and free_right is None:
            left = queue.popleft()
            for right in adjacency[left]:
                if right in parent_right:
                    continue
                parent_right[right] = left
                if right not in right_matches:
                    free_right = right
                    break
                next_left = right_matches[right]
                if next_left not in seen_left:
                    seen_left.add(next_left)
                    queue.append(next_left)
        if free_right is None:
            return False
        right = free_right
        while True:
            left = parent_right[right]
            previous_right = left_matches.get(left)
            left_matches[left] = right
            right_matches[right] = left
            if previous_right is None:
                break
            right = previous_right
    return True


def compare_results(actual: ResultTable, gold: ResultTable, spec: ComparisonSpec) -> ComparisonResult:
    if len(gold.columns) != spec.column_count:
        raise EvaluationError("Gold result does not match the approved column contract")
    if len(actual.columns) != spec.column_count:
        return ComparisonResult(0, "column_count_mismatch")
    if any(len(row) != spec.column_count for row in gold.rows + actual.rows):
        raise EvaluationError("Result row width does not match column metadata")
    if len(actual.rows) != len(gold.rows):
        return ComparisonResult(0, "row_count_mismatch")
    if spec.ordered:
        equivalent = all(rows_match(left, right, spec) for left, right in zip(actual.rows, gold.rows, strict=True))
    elif not spec.approximate_columns:
        equivalent = Counter(tuple(map(cell_key, row)) for row in actual.rows) == Counter(tuple(map(cell_key, row)) for row in gold.rows)
    else:
        # Exact columns partition rows without collapsing their multiplicities.
        exact_indices = [i for i in range(spec.column_count) if i not in spec.approximate_columns]
        def grouped(rows):
            groups = defaultdict(list)
            for row in rows:
                groups[tuple(cell_key(row[i]) for i in exact_indices)].append(row)
            return groups
        actual_groups, gold_groups = grouped(actual.rows), grouped(gold.rows)
        equivalent = actual_groups.keys() == gold_groups.keys()
        if equivalent:
            for key, references in gold_groups.items():
                candidates = actual_groups[key]
                if len(candidates) != len(references) or not has_perfect_matching(candidates, references, spec):
                    equivalent = False
                    break
    return ComparisonResult(int(equivalent), "equivalent" if equivalent else "value_or_order_mismatch")

