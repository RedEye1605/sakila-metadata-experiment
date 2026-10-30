from datetime import date
from decimal import Decimal
from itertools import permutations
import random

import pytest

from sakila_experiment.contracts import GoldReference
from sakila_experiment.db.execute import ResultTable
from sakila_experiment.evaluation.compare import (
    ComparisonSpec, EvaluationError, compare_results, comparison_spec,
)


def table(rows, width=None, labels=None):
    width = width if width is not None else len(rows[0])
    return ResultTable(labels or tuple(f"c{i}" for i in range(width)), (0,) * width, tuple(rows))


def spec(width, **kwargs):
    return ComparisonSpec(width, column_order="permutation", **kwargs)


def test_reordered_names_and_revenue_use_one_global_column_mapping():
    gold = table((("Ayu", Decimal("12.50")), ("Budi", Decimal("8.00"))))
    actual = table(((8, "Budi"), (Decimal("12.5"), "Ayu")), labels=("earnings", "person"))
    result = compare_results(actual, gold, spec(2))
    assert result.execution_accuracy == 1
    assert result.column_permutation == (1, 0)
    assert compare_results(actual, gold, ComparisonSpec(2)).execution_accuracy == 0


def test_equal_marginals_do_not_allow_cross_person_revenue_reassignment():
    gold = table((("Ayu", 12), ("Budi", 8)))
    actual = table(((8, "Ayu"), (12, "Budi")))
    assert compare_results(actual, gold, spec(2)).execution_accuracy == 0


def test_cannot_choose_a_different_column_permutation_for_each_row():
    gold = table(((1, 2), (3, 4)))
    actual = table(((2, 1), (3, 4)))
    assert compare_results(actual, gold, spec(2)).execution_accuracy == 0


def test_duplicate_rows_and_duplicate_columns_retain_multiplicity():
    gold = table(((1, 1, "a"), (1, 1, "a"), (2, 2, "b")))
    actual = table((("a", 1, 1), ("b", 2, 2), ("a", 1, 1)))
    assert compare_results(actual, gold, spec(3)).execution_accuracy == 1
    wrong = table((("a", 1, 1), ("b", 2, 2), ("b", 2, 2)))
    assert compare_results(wrong, gold, spec(3)).execution_accuracy == 0


def test_ordered_rows_still_matched_after_column_permutation():
    gold = table((("Ayu", 12), ("Budi", 8)))
    correct = table(((12, "Ayu"), (8, "Budi")))
    reversed_rows = table(tuple(reversed(correct.rows)))
    assert compare_results(correct, gold, spec(2, ordered=True)).execution_accuracy == 1
    assert compare_results(reversed_rows, gold, spec(2, ordered=True)).execution_accuracy == 0
    assert compare_results(reversed_rows, gold, spec(2)).execution_accuracy == 1


def test_empty_outputs_require_the_same_column_count():
    assert compare_results(table((), 2), table((), 2), spec(2)).execution_accuracy == 1
    assert compare_results(table((), 1), table((), 2), spec(2)).execution_accuracy == 0


def test_nulls_and_numeric_strings_are_not_lossily_coerced():
    gold = table(((None, 1), ("NULL", 2)))
    assert compare_results(table(((2, "NULL"), (1, None))), gold, spec(2)).execution_accuracy == 1
    assert compare_results(table((("2", "NULL"), (1, None))), gold, spec(2)).execution_accuracy == 0


def test_tolerance_and_dates_follow_gold_column_positions_after_mapping():
    gold = table((("Ayu", Decimal("1.2345"), date(2005, 7, 1)),))
    actual = table((("2005-07-01", "Ayu", 1.2345),))
    result = compare_results(actual, gold, spec(3, approximate_columns=(1,), date_columns=(2,)))
    assert result.execution_accuracy == 1 and result.column_permutation == (1, 2, 0)
    assert compare_results(table((("2005-07-01", "Ayu", 1.2346),)), gold,
                           spec(3, approximate_columns=(1,), date_columns=(2,))).execution_accuracy == 0


def test_exact_money_does_not_inherit_tolerance_from_another_numeric_column():
    gold = table(((Decimal("10.00"), Decimal("0.1234")),))
    actual = table(((0.1234, Decimal("10.00000000001")),))
    assert compare_results(actual, gold, spec(2, approximate_columns=(1,))).execution_accuracy == 0


def test_approximate_matching_needs_non_greedy_row_and_column_assignment():
    gold = table(((Decimal("0.1"), "same"), (Decimal("0.0"), "same")))
    actual = table((("same", Decimal("0.1")), ("same", Decimal("0.2"))))
    result = compare_results(actual, gold, spec(2, approximate_columns=(0,),
                                             absolute_tolerance="0.11", relative_tolerance="0"))
    assert result.execution_accuracy == 1 and result.column_permutation == (1, 0)


def test_search_exhaustion_is_an_evaluator_incident_never_a_model_zero():
    gold = table(((1, 1, 0), (0, 0, 1)))
    actual = table(((1, 0, 1), (0, 1, 0)))
    with pytest.raises(EvaluationError, match="search budget"):
        compare_results(actual, gold, spec(3, ordered=True, max_column_search_nodes=1))


def test_ordered_equal_column_bags_use_aligned_values_to_avoid_factorial_search():
    gold = table(tuple(tuple((r + c) % 8 for c in range(8)) for r in range(8)))
    actual = table(tuple(tuple(reversed(row)) for row in gold.rows))
    result = compare_results(actual, gold, spec(8, ordered=True))
    assert result.execution_accuracy == 1 and result.column_permutation == tuple(reversed(range(8)))


def test_large_exact_tolerant_self_comparison_avoids_quadratic_search():
    rows = tuple((Decimal(i),) for i in range(1100))
    assert compare_results(table(rows), table(rows), spec(1, approximate_columns=(0,))).execution_accuracy == 1
    with pytest.raises(EvaluationError, match="Approximate matching"):
        compare_results(table(rows), table(rows), ComparisonSpec(1, approximate_columns=(0,)))


def test_total_approximate_work_is_bounded_across_distinct_row_groups(monkeypatch):
    from sakila_experiment.evaluation import compare
    gold = table(tuple((label, Decimal("0.1")) for label in ("a", "b") for _ in range(3)))
    actual = table(tuple((Decimal("0.11"), label) for label in ("a", "b") for _ in range(3)))
    monkeypatch.setattr(compare, "_MAX_MATCHING_WORK", 30)
    with pytest.raises(EvaluationError, match="total-work budget"):
        compare_results(actual, gold, spec(2, approximate_columns=(1,), absolute_tolerance="0.02"))


def test_relative_tolerance_remains_anchored_to_gold_after_column_mapping():
    gold = table(((100, "tag"),))
    contract = spec(2, approximate_columns=(0,), absolute_tolerance="0", relative_tolerance="0.1")
    assert compare_results(table((("tag", 109),)), gold, contract).execution_accuracy == 1
    assert compare_results(table((("tag", 111),)), gold, contract).execution_accuracy == 0


def test_total_approximate_work_is_bounded_across_column_permutations(monkeypatch):
    from sakila_experiment.evaluation import compare
    gold = table(((0, 1), (1, 0)))
    actual = table(((Decimal("0.1"), Decimal("0.1")), (Decimal("1.1"), Decimal("1.1"))))
    monkeypatch.setattr(compare, "_MAX_MATCHING_WORK", 12)
    with pytest.raises(EvaluationError, match="total-work budget"):
        compare_results(actual, gold, spec(2, approximate_columns=(0, 1),
                                          absolute_tolerance="0.2", relative_tolerance="0"))


def test_malformed_row_and_nonfinite_values_are_evaluator_errors():
    with pytest.raises(EvaluationError, match="row width"):
        compare_results(table(((1,),), 2), table(((1, 2),)), spec(2))
    with pytest.raises(EvaluationError, match="Non-finite"):
        compare_results(table(((float("inf"),),)), table(((1,),)), spec(1))


def test_gold_contract_explicitly_selects_the_new_policy():
    legacy = GoldReference(question_id="Q001", sql="SELECT 1", column_count=1)
    revised = legacy.model_copy(update={"column_order": "permutation"})
    assert comparison_spec(legacy).column_order == "fixed"
    assert comparison_spec(revised).column_order == "permutation"


def test_bounded_random_relations_match_exhaustive_exact_oracle():
    rng = random.Random(2026102804)
    from collections import Counter
    for width in (1, 2, 3, 4):
        for _ in range(40):
            gold = tuple(tuple(rng.randrange(3) for _ in range(width)) for _ in range(4))
            actual = tuple(tuple(rng.randrange(3) for _ in range(width)) for _ in range(4))
            if rng.randrange(2):
                permutation = rng.sample(range(width), width)
                actual = tuple(tuple(row[i] for i in permutation) for row in reversed(gold))
            for ordered in (False, True):
                expected = any((tuple(tuple(row[i] for i in p) for row in actual) == gold if ordered
                                else Counter(tuple(row[i] for i in p) for row in actual) == Counter(gold))
                               for p in permutations(range(width)))
                assert compare_results(table(actual), table(gold), spec(width, ordered=ordered)).execution_accuracy == expected


@pytest.mark.parametrize("budget", [0, -1, True])
def test_invalid_search_budget_is_rejected(budget):
    with pytest.raises(EvaluationError):
        spec(2, max_column_search_nodes=budget)
