from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from sakila_experiment.contracts import GoldReference
from sakila_experiment.db.execute import QueryExecution, ResultTable
from sakila_experiment.evaluation import robustness


def test_auxiliary_scores_exact_stored_sql_and_preserves_date_and_duplicates(monkeypatch):
    reference = GoldReference(question_id="Q101", sql="SELECT DATE(payment_date),COUNT(*) FROM payment GROUP BY DATE(payment_date)",
                              column_count=2, date_columns=(0,))
    gold = SimpleNamespace(result=ResultTable(("date", "n"), (10, 3), ((date(2005, 7, 1), 2), (date(2005, 7, 1), 2))))
    result = ResultTable(("other_alias", "n"), (253, 3), (("2005-07-01", Decimal("2.00")), ("2005-07-01", Decimal("2.00"))))
    calls = []
    def execute(config, sql, tables):
        calls.append(sql)
        return QueryExecution("success", "accepted", result, "a" * 64, 1)
    monkeypatch.setattr(robustness, "execute_sql", execute)
    stored = "SELECT DATE_FORMAT(payment_date,'%Y-%m-%d'), COUNT(*) FROM payment GROUP BY DATE(payment_date)"
    outcome, _ = robustness.score_prediction(None, frozenset({"payment"}), {"extracted_sql": stored}, reference, gold)
    assert outcome["execution_accuracy"] == 1 and calls == [stored]
    # Missing one duplicate is a semantic difference even when sets agree.
    gold.result = ResultTable(gold.result.columns, gold.result.type_codes, gold.result.rows[:1])
    outcome, _ = robustness.score_prediction(None, frozenset({"payment"}), {"extracted_sql": stored}, reference, gold)
    assert outcome["execution_accuracy"] == 0


def test_auxiliary_infrastructure_has_no_score_and_missing_sql_is_not_dispatched(monkeypatch):
    def unavailable(*args):
        return QueryExecution("infrastructure_error", "accepted", error_code=2003)
    monkeypatch.setattr(robustness, "execute_sql", unavailable)
    reference = GoldReference(question_id="Q101", sql="SELECT 1", column_count=1)
    with pytest.raises(robustness.RobustnessError, match="no EX"):
        robustness.score_prediction(None, frozenset(), {"extracted_sql": "SELECT 1"}, reference, None)
    outcome, result = robustness.score_prediction(None, frozenset(), {"extracted_sql": None}, reference, None)
    assert outcome["execution_accuracy"] == 0 and result is None
