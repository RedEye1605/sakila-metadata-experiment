"""Versioned, duplicate-preserving execution-result comparison.

Exact comparisons use rational numeric values, never lossy rounding. Optional
approximate columns use a complete one-to-one row matching, not greedy pairing.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING, Literal

from ..db.execute import ResultTable
from ..db.values import encode_value

COMPARATOR_VERSION = "ex-results-v1"
COLUMN_PERMUTATION_VERSION = "ex-results-v3-column-permutation"
_MAX_MATCHING_WORK = 10000000

if TYPE_CHECKING:
    from ..contracts import GoldReference


class EvaluationError(RuntimeError):
    """An evaluator/contract issue, not a model failure."""


@dataclass(frozen=True)
class ComparisonSpec:
    column_count: int
    ordered: bool = False
    approximate_columns: tuple[int, ...] = ()
    absolute_tolerance: str = "1e-9"
    relative_tolerance: str = "1e-12"
    date_columns: tuple[int, ...] = ()
    column_order: Literal["fixed", "permutation"] = "fixed"
    max_column_search_nodes: int = 10000

    def __post_init__(self):
        if self.column_count < 1:
            raise EvaluationError("Comparison requires a positive column count")
        if self.column_order not in {"fixed", "permutation"}:
            raise EvaluationError("Unknown column-order comparison policy")
        if self.column_order == "permutation" and self.column_count > 32:
            raise EvaluationError("Column matching exceeds the reviewed width budget")
        if type(self.max_column_search_nodes) is not int or self.max_column_search_nodes < 1:
            raise EvaluationError("Column matching requires a positive search budget")
        if len(set(self.approximate_columns)) != len(self.approximate_columns) or any(i < 0 or i >= self.column_count for i in self.approximate_columns):
            raise EvaluationError("Invalid approximate-column contract")
        if len(set(self.date_columns)) != len(self.date_columns) or any(type(i) is not int or i < 0 or i >= self.column_count for i in self.date_columns):
            raise EvaluationError("Invalid date-column contract")
        if set(self.date_columns) & set(self.approximate_columns):
            raise EvaluationError("A column cannot be both numeric-approximate and date")
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
    # Gold column i is supplied by actual column column_permutation[i].
    column_permutation: tuple[int, ...] | None = None


def comparison_spec(reference: GoldReference) -> ComparisonSpec:
    """Keep tolerance/date indices in the reference's coordinate system."""
    return ComparisonSpec(reference.column_count, reference.ordered, reference.approximate_columns,
                          date_columns=reference.date_columns, column_order=reference.column_order)


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


def contracted_key(value, column: int, spec: ComparisonSpec):
    # Opt-in ISO calendar-date representation; do not coerce timestamps,
    # arbitrary strings, NULL, or numeric text. Legacy comparisons unchanged.
    if column in spec.date_columns:
        if type(value) is date:
            return ("calendar_date", value.isoformat())
        if isinstance(value, str):
            try:
                parsed = date.fromisoformat(value)
                if parsed.isoformat() == value:
                    return ("calendar_date", value)
            except ValueError:
                pass
    return cell_key(value)


def _cells_match(left, right, column: int, spec: ComparisonSpec) -> bool:
    if column in spec.approximate_columns:
        a, b = numeric(left), numeric(right)
        if a is not None and b is not None:
            tolerance = Fraction(Decimal(spec.absolute_tolerance)) + Fraction(Decimal(spec.relative_tolerance)) * abs(b)
            return abs(a - b) <= tolerance
    return contracted_key(left, column, spec) == contracted_key(right, column, spec)


def rows_match(actual: tuple, gold: tuple, spec: ComparisonSpec) -> bool:
    return all(_cells_match(left, right, column, spec)
               for column, (left, right) in enumerate(zip(actual, gold, strict=True)))


def _charge_matching_work(work: list[int] | None, amount: int):
    if work is not None:
        work[0] += amount
        if work[0] > _MAX_MATCHING_WORK:
            raise EvaluationError("Approximate column matching exceeds the reviewed total-work budget")


def has_perfect_matching(actual: list[tuple], gold: list[tuple], spec: ComparisonSpec,
                         *, work: list[int] | None = None) -> bool:
    if len(actual) * len(gold) > 1000000:
        raise EvaluationError("Approximate matching exceeds the reviewed comparison budget")
    _charge_matching_work(work, len(actual) * len(gold) * spec.column_count)
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
                _charge_matching_work(work, 1)
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


def _rows_equivalent(actual_rows: tuple, gold_rows: tuple, spec: ComparisonSpec,
                     *, work: list[int] | None = None) -> bool:
    if spec.ordered:
        return all(rows_match(left, right, spec) for left, right in zip(actual_rows, gold_rows, strict=True))
    # Preserve the legacy approximate-matching budget behavior. Only v3 adds
    # the exact fast path for otherwise tolerant contracts.
    if not spec.approximate_columns or spec.column_order == "permutation":
        exact = Counter(tuple(contracted_key(value, i, spec) for i, value in enumerate(row)) for row in actual_rows) == Counter(tuple(contracted_key(value, i, spec) for i, value in enumerate(row)) for row in gold_rows)
        if exact or not spec.approximate_columns:
            return exact
    if spec.approximate_columns:
        # Exact columns partition rows without collapsing their multiplicities.
        exact_indices = [i for i in range(spec.column_count) if i not in spec.approximate_columns]
        def grouped(rows):
            groups = defaultdict(list)
            for row in rows:
                groups[tuple(contracted_key(row[i], i, spec) for i in exact_indices)].append(row)
            return groups
        actual_groups, gold_groups = grouped(actual_rows), grouped(gold_rows)
        equivalent = actual_groups.keys() == gold_groups.keys()
        if equivalent:
            for key, references in gold_groups.items():
                candidates = actual_groups[key]
                if len(candidates) != len(references) or not has_perfect_matching(candidates, references, spec, work=work):
                    equivalent = False
                    break
        return equivalent


def _column_signature(rows: tuple, source: int, target: int, spec: ComparisonSpec):
    """Necessary marginal constraints only; whole rows decide equivalence."""
    if target not in spec.approximate_columns:
        if spec.ordered:
            return tuple(contracted_key(row[source], target, spec) for row in rows)
        return Counter(contracted_key(row[source], target, spec) for row in rows)
    numbers, other = 0, Counter()
    for row in rows:
        if numeric(row[source]) is not None:
            numbers += 1
        else:
            other[contracted_key(row[source], target, spec)] += 1
    return numbers, other


def _column_permutation(actual: tuple, gold: tuple, spec: ComparisonSpec) -> tuple[int, ...] | None:
    width = spec.column_count
    if len(actual) * width * width > 10000000:
        raise EvaluationError("Column constraints exceed the reviewed cell-comparison budget")
    candidates = {}
    for target in range(width):
        expected = _column_signature(gold, target, target, spec)
        candidates[target] = [source for source in range(width)
                              if _column_signature(actual, source, target, spec) == expected
                              and (not spec.ordered or target not in spec.approximate_columns
                                   or all(_cells_match(a[source], g[target], target, spec)
                                          for a, g in zip(actual, gold, strict=True)))]
        if not candidates[target]:
            return None
    # A single global bijection must preserve every row's associations. Neither
    # equal column bags nor sorting cells separately is sufficient evidence.
    targets = sorted(range(width), key=lambda i: (len(candidates[i]), i))
    mapping, used, visited = [-1] * width, set(), 0
    compared_cells, matching_work = 0, [0]

    def search(depth):
        nonlocal visited, compared_cells
        if depth == width:
            compared_cells += len(actual) * width
            if compared_cells > 10000000:
                raise EvaluationError("Column matching exceeds the reviewed cell-comparison budget")
            permuted = tuple(tuple(row[i] for i in mapping) for row in actual)
            return tuple(mapping) if _rows_equivalent(permuted, gold, spec, work=matching_work) else None
        target = targets[depth]
        for source in candidates[target]:
            if source in used:
                continue
            visited += 1
            if visited > spec.max_column_search_nodes:
                raise EvaluationError("Column matching exceeds the reviewed search budget")
            mapping[target] = source
            used.add(source)
            result = search(depth + 1)
            used.remove(source)
            if result is not None:
                return result
        return None

    return search(0)


def compare_results(actual: ResultTable, gold: ResultTable, spec: ComparisonSpec) -> ComparisonResult:
    if len(gold.columns) != spec.column_count:
        raise EvaluationError("Gold result does not match the approved column contract")
    if len(actual.columns) != spec.column_count:
        return ComparisonResult(0, "column_count_mismatch")
    if any(len(row) != spec.column_count for row in gold.rows + actual.rows):
        raise EvaluationError("Result row width does not match column metadata")
    if len(actual.rows) != len(gold.rows):
        return ComparisonResult(0, "row_count_mismatch")
    if spec.column_order == "permutation":
        # Empty outputs still need equal width. Their column identity cannot be
        # inferred from values; record that limitation instead of using aliases.
        if not gold.rows:
            return ComparisonResult(1, "equivalent_empty_results", tuple(range(spec.column_count)))
        permutation = _column_permutation(actual.rows, gold.rows, spec)
        return ComparisonResult(int(permutation is not None),
                                "equivalent" if permutation is not None else "no_equivalent_column_bijection", permutation)
    equivalent = _rows_equivalent(actual.rows, gold.rows, spec)
    return ComparisonResult(int(equivalent), "equivalent" if equivalent else "value_or_order_mismatch")

