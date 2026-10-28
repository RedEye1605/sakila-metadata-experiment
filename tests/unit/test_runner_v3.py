from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from sakila_experiment.contracts import GoldReference, Question
from sakila_experiment.db.execute import QueryExecution, ResultTable
from sakila_experiment.experiment import runner
from test_runner import setup_pilot


def test_main_question_attributes_are_keyed_by_ids_from_question_objects():
    questions = (Question(question_id="Q102", question="Berapa jumlah pembayaran?", complexity="simple"),)
    references = {"Q102": GoldReference(question_id="Q102", sql="SELECT COUNT(*) FROM payment", column_count=1)}
    contracts = {"Q102": {"primary_need": "schema_mapping", "semantic_family": "payment-cardinality"}}
    assert runner._question_attributes(questions, references, contracts) == {
        "Q102": {"primary_need": "schema_mapping", "semantic_family": "payment-cardinality", "spider_level": "easy"}}


def test_runner_scores_and_logs_reordered_projection_without_changing_sql(tmp_path, monkeypatch):
    config, _, _, reference, success, response, calls = setup_pilot(tmp_path, monkeypatch)
    reference = reference.model_copy(update={"column_count": 2, "column_order": "permutation"})
    gold_table = ResultTable(("name", "revenue"), (0, 0), (("Ayu", Decimal("12.50")), ("Budi", Decimal("8.00"))))
    actual_table = ResultTable(("arbitrary_alias", "another_alias"), (0, 0), ((8, "Budi"), (Decimal("12.5"), "Ayu")))
    gold = replace(success, result=gold_table)
    actual = replace(success, result=actual_table)
    monkeypatch.setattr(runner, "execute_sql", lambda *args: actual)
    outcome, result = runner.evaluate_response(config, frozenset({"actor"}), response, reference, gold)
    assert outcome["execution_accuracy"] == 1
    assert outcome["column_permutation"] == (1, 0)
    assert outcome["column_order_policy"] == "permutation"
    assert outcome["extracted_sql"] == response.text and result == actual_table
    assert not calls


def test_new_comparator_policy_does_not_allow_extra_projection_columns(tmp_path, monkeypatch):
    config, _, _, reference, success, response, _ = setup_pilot(tmp_path, monkeypatch)
    reference = reference.model_copy(update={"column_order": "permutation"})
    actual = replace(success, result=ResultTable(("a", "extra"), (0, 0), ((200, 7),)))
    monkeypatch.setattr(runner, "execute_sql", lambda *args: actual)
    outcome, _ = runner.evaluate_response(config, frozenset({"actor"}), response, reference, success)
    assert outcome["execution_accuracy"] == 0 and outcome["comparison_reason"] == "column_count_mismatch"
