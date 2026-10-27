from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from sakila_experiment.db.execute import ResultTable
from sakila_experiment.evaluation.compare import ComparisonSpec, EvaluationError, compare_results


def result(rows, columns=None):
    width = len(rows[0]) if rows else 1
    labels = columns or tuple(f"c{i}" for i in range(width))
    return ResultTable(labels, (0,) * len(labels), tuple(map(tuple, rows)))


def score(actual, gold, *, ordered=False, columns=1, approximate=()):
    return compare_results(result(actual), result(gold), ComparisonSpec(columns, ordered, approximate)).execution_accuracy


def test_unordered_comparison_preserves_duplicate_counts():
    assert score([(1,), (2,), (1,)], [(1,), (1,), (2,)]) == 1
    assert score([(1,), (2,), (2,)], [(1,), (1,), (2,)]) == 0


def test_ordered_results_require_the_requested_order():
    assert score([(2,), (1,)], [(1,), (2,)], ordered=True) == 0
    assert score([(2,), (1,)], [(1,), (2,)]) == 1


def test_column_positions_are_preserved_while_aliases_are_ignored():
    assert compare_results(result([(1, 2)], ("renamed", "other")), result([(1, 2)], ("a", "b")), ComparisonSpec(2)).execution_accuracy == 1
    assert score([(2, 1)], [(1, 2)], columns=2) == 0
    assert compare_results(result([(1, 2)]), result([(1,)]), ComparisonSpec(1)).execution_accuracy == 0


def test_null_text_and_zero_are_distinct():
    for value in ("NULL", "", 0):
        assert score([(value,)], [(None,)]) == 0
    assert score([(None,)], [(None,)]) == 1


def test_exact_numeric_comparison_does_not_lose_precision():
    assert score([(Decimal("1.00"),)], [(1,)]) == 1
    assert score([(1.0,)], [(1,)]) == 1
    assert score([(9007199254740992,)], [(9007199254740993,)]) == 0
    assert score([(Decimal("0.100000000000000000000000000001"),)], [(Decimal("0.1"),)]) == 0
    assert score([("1",)], [(1,)]) == 0


def test_approximation_requires_an_explicit_column_contract():
    assert score([(0.1,)], [(Decimal("0.1"),)]) == 0
    assert score([(0.1,)], [(Decimal("0.1"),)], approximate=(0,)) == 1
    assert score([(0.1001,)], [(Decimal("0.1"),)], approximate=(0,)) == 0


def test_approximate_matching_uses_augmenting_paths_not_greedy_matching():
    # Greedy 0.1 -> 0.1 would prevent the only complete matching.
    spec = ComparisonSpec(1, approximate_columns=(0,), absolute_tolerance="0.11", relative_tolerance="0")
    assert compare_results(result([(Decimal("0.1"),), (Decimal("0.2"),)]), result([(Decimal("0.1"),), (Decimal("0.0"),)]), spec).execution_accuracy == 1


def test_matching_does_not_compare_independent_column_sets():
    assert score([(1, "a"), (2, "b")], [(1, "b"), (2, "a")], columns=2) == 0


def test_empty_results_still_check_column_contract():
    assert score([], []) == 1
    actual = ResultTable(("a", "b"), (0, 0), ())
    assert compare_results(actual, result([]), ComparisonSpec(1)).execution_accuracy == 0


def test_date_time_binary_and_text_are_not_lossily_coerced():
    assert score([(date(2005, 1, 1),)], [(datetime(2005, 1, 1),)]) == 0
    assert score([(b"\x00\xff",)], [(b"\x00\xff",)]) == 1
    assert score([("ABC ",)], [("abc",)]) == 0
    a = datetime(2005, 1, 1, 7, tzinfo=timezone(timedelta(hours=7)))
    b = datetime(2005, 1, 1, tzinfo=timezone.utc)
    assert score([(a,)], [(b,)]) == 1


def test_nonfinite_values_and_invalid_gold_are_evaluator_failures():
    with pytest.raises(EvaluationError):
        score([(float("nan"),)], [(1,)])
    with pytest.raises(EvaluationError):
        compare_results(result([(1,)]), result([(1, 2)]), ComparisonSpec(1))

