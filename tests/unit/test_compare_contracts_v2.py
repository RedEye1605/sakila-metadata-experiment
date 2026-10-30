from datetime import date, datetime
from decimal import Decimal

import pytest

from sakila_experiment.db.execute import ResultTable
from sakila_experiment.evaluation.compare import ComparisonSpec, EvaluationError, compare_results


def table(*rows):
    width = len(rows[0])
    return ResultTable(tuple(str(i) for i in range(width)), tuple(0 for _ in range(width)), tuple(rows))


def test_calendar_date_text_is_opt_in_and_preserves_multiplicity_and_granularity():
    expected = table((date(2005, 7, 1),), (date(2005, 7, 1),))
    actual = table(("2005-07-01",), ("2005-07-01",))
    assert compare_results(actual, expected, ComparisonSpec(1)).execution_accuracy == 0
    spec = ComparisonSpec(1, date_columns=(0,))
    assert compare_results(actual, expected, spec).execution_accuracy == 1
    assert compare_results(table(("2005-07-01",)), expected, spec).execution_accuracy == 0
    for invalid in ("20050701", "2005-7-1", "2005-07-01T00:00:00", datetime(2005, 7, 1), None, 20050701):
        assert compare_results(table((invalid,), (invalid,)), expected, spec).execution_accuracy == 0


def test_prespecified_numeric_column_tolerance_allows_binary_representation_not_wrong_precision():
    spec = ComparisonSpec(1, approximate_columns=(0,))
    expected = table((Decimal("1.2345"),))
    assert compare_results(table((1.2345,)), expected, spec).execution_accuracy == 1
    assert compare_results(table((1.23456,)), expected, spec).execution_accuracy == 0
    assert compare_results(table(("1.2345",)), expected, spec).execution_accuracy == 0


def test_incompatible_or_invalid_semantic_column_contracts_rejected():
    for dates, approximate in [((0,), (0,)), ((1,), ()), ((True,), ())]:
        with pytest.raises(EvaluationError):
            ComparisonSpec(1, date_columns=dates, approximate_columns=approximate)
