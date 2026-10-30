from pathlib import Path

import pytest

from sakila_experiment.config import load_config
from sakila_experiment.db.execute import ResultTable, execute_sql
from sakila_experiment.db.inspect import inspect_database
from sakila_experiment.evaluation.compare import ComparisonSpec, compare_results

pytestmark = pytest.mark.integration
ROOT = Path(__file__).parents[2]


def test_actual_mysql_name_payment_columns_can_swap_without_losing_requested_ranking():
    config = load_config(ROOT / "configs/revision03.toml")
    tables = frozenset(t["name"] for t in inspect_database(config)["technical_schema"]["tables"])
    suffix = " FROM customer c JOIN payment p ON p.customer_id=c.customer_id GROUP BY c.customer_id ORDER BY SUM(p.amount) DESC,c.customer_id ASC LIMIT 5"
    gold = execute_sql(config, "SELECT c.first_name,SUM(p.amount)" + suffix, tables)
    actual = execute_sql(config, "SELECT SUM(p.amount) AS arbitrary_value,c.first_name AS arbitrary_label" + suffix, tables)
    assert gold.status == actual.status == "success"
    contract = ComparisonSpec(2, ordered=True, column_order="permutation")
    comparison = compare_results(actual.result, gold.result, contract)
    assert comparison.execution_accuracy == 1 and comparison.column_permutation == (1, 0)
    reversed_rows = ResultTable(actual.result.columns, actual.result.type_codes, tuple(reversed(actual.result.rows)))
    assert compare_results(reversed_rows, gold.result, contract).execution_accuracy == 0
