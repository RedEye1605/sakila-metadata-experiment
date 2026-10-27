import pytest

from sakila_experiment.evaluation.safety import extract_sql, validate_sql

TABLES = frozenset({"film", "payment", "customer"})


@pytest.mark.parametrize("sql", [
    "SELECT COUNT(*) FROM film",
    "SELECT 'a;b' AS value;",
    "WITH f AS (SELECT film_id FROM film) SELECT * FROM f",
    "SELECT * FROM (SELECT film_id FROM film) AS f",
    "SELECT film_id FROM film UNION ALL SELECT film_id FROM film",
    "SELECT COALESCE(SUM(amount),0) FROM sakila.payment",
    "SELECT '/*!80000 not a comment */'",
    "SELECT ROW_NUMBER() OVER (ORDER BY film_id) FROM film",
    "SELECT film_id FROM film f WHERE NOT EXISTS (SELECT 1 FROM payment p WHERE p.rental_id=f.film_id)",
    "SELECT * FROM film WHERE length>120 AND (rating='PG' OR rating='G')",
])
def test_safe_read_queries_are_accepted(sql):
    assert validate_sql(sql, TABLES).accepted


@pytest.mark.parametrize("sql", [
    "", "SELECT 1; SELECT 2", "DROP TABLE film", "DELETE FROM film WHERE 1=0",
    "UPDATE film SET title='bad'", "SHOW TABLES", "EXPLAIN SELECT * FROM film",
    "SELECT SLEEP(1)", "SELECT BENCHMARK(100,1)", "SELECT LOAD_FILE('/etc/passwd')",
    "SELECT GET_LOCK('x',1)", "SELECT RELEASE_LOCK('x')", "SELECT RAND()", "SELECT NOW()",
    "SELECT @@version", "SELECT @a := 1", "SELECT * FROM film FOR UPDATE",
    "SELECT /*+ MAX_EXECUTION_TIME(999999) */ * FROM film",
    "SELECT /*!80000 SQL_NO_CACHE */ 1", "SELECT * FROM mysql.user",
    "SELECT * FROM information_schema.tables", "SELECT * FROM actor",
    "WITH film AS (SELECT * FROM mysql.user) SELECT * FROM film",
    "WITH f AS (SELECT * FROM film) SELECT * FROM other.f",
    "SELECT sakila.custom_function(1)", "SELECT 1 INTO OUTFILE '/tmp/result'",
    "SELECT EXISTS(SELECT 1 FROM mysql.user)",
    "SELECT * FROM film WHERE film_id=1 OR SLEEP(1)=0",
    "SELECT * FROM film INTO DUMPFILE '/tmp/result'", "SELECT missing(",
])
def test_unsafe_or_unauthorized_queries_are_rejected(sql):
    assert not validate_sql(sql, TABLES).accepted


def test_extraction_never_repairs_or_selects_a_query_fragment():
    assert extract_sql("  ```sql\nSELECT * FROM film;\n``` ") == "SELECT * FROM film;"
    text = "Explanation\n```sql\nSELECT * FROM film;\n```"
    assert extract_sql(text) == text
    assert not validate_sql(extract_sql(text), TABLES).accepted

