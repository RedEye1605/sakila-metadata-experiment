import pytest

from sakila_experiment.evaluation.safety import validate_sql

TABLES = frozenset({"film", "rental"})


@pytest.mark.parametrize("sql", [
    "SELECT HOUR(rental_date) FROM rental",
    "SELECT FIND_IN_SET('Commentaries',special_features) FROM film",
    "SELECT DAYNAME(return_date) FROM rental",
    "SELECT MINUTE(rental_date),SECOND(rental_date) FROM rental",
    "SELECT LOCATE('A',title),INSTR(title,'A') FROM film",
    "SELECT title FROM film WHERE REGEXP_LIKE(title,'^A')",
    "SELECT STR_TO_DATE('2005-07-01','%Y-%m-%d'),LAST_DAY('2005-07-01')",
    "SELECT HOUR(rental_date),COUNT(*) FROM rental GROUP BY HOUR(rental_date) HAVING COUNT(*)>=ALL(SELECT COUNT(*) FROM rental GROUP BY HOUR(rental_date))",
])
def test_documented_native_alternatives_are_opt_in_without_changing_legacy(sql):
    assert not validate_sql(sql, TABLES).accepted
    assert validate_sql(sql, TABLES, policy_version="mysql-readonly-v2").accepted


@pytest.mark.parametrize("sql", [
    "SELECT SLEEP(1)", "SELECT BENCHMARK(1000,1)", "SELECT GET_LOCK('x',1)",
    "SELECT LOAD_FILE('/etc/passwd')", "SELECT sakila.custom_function(1)", "SELECT custom_function(1)",
    "SELECT * FROM information_schema.tables", "SELECT 1 INTO OUTFILE '/tmp/output'", "SELECT 1;SELECT 2",
    "UPDATE film SET title=title", "SELECT RAND()", "SELECT CURRENT_TIMESTAMP()",
])
def test_v2_retains_unsafe_unknown_and_uncontrolled_clock_rejection(sql):
    assert not validate_sql(sql, TABLES, policy_version="mysql-readonly-v2").accepted


def test_unknown_policy_is_rejected_and_quantifiers_are_not_function_calls():
    assert validate_sql("SELECT 1", TABLES, policy_version="unknown").code == "unknown_sql_policy"
    for policy in ("mysql-readonly-v1", "mysql-readonly-v2"):
        assert validate_sql("SELECT 1 WHERE 1>=ALL(SELECT 1)", TABLES, policy_version=policy).accepted
        assert validate_sql("SELECT 1 WHERE 1=ANY(SELECT 1)", TABLES, policy_version=policy).accepted
