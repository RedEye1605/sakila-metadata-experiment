from pathlib import Path

import pymysql
import pytest

from sakila_experiment.config import load_config
from sakila_experiment.db.connection import read_connection
from sakila_experiment.db.execute import execute_sql
from sakila_experiment.db.inspect import inspect_database, verify_fingerprint

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def config():
    return load_config(Path(__file__).resolve().parents[2] / "configs/local.toml")


@pytest.fixture(scope="module")
def inventory(config):
    return inspect_database(config)


@pytest.fixture(scope="module")
def tables(inventory):
    return frozenset(table["name"] for table in inventory["technical_schema"]["tables"])


def test_official_installation_is_frozen_and_has_complete_constraints(inventory):
    assert inventory["server"]["read_only"] == 1
    assert inventory["server"]["super_read_only"] == 1
    assert inventory["server"]["time_zone"] == "+00:00"
    tables = {table["name"]: table for table in inventory["technical_schema"]["tables"]}
    assert "film" in tables and "language" in tables and "film_text" in tables
    assert tables["film_actor"]["primary_key"] == ["actor_id", "film_id"]
    assert any(key["target_table"] == "film" for key in tables["film_actor"]["foreign_keys"])
    counts = {table["table"]: table["row_count"] for table in inventory["table_content"]}
    assert counts["film"] == counts["film_text"] == 1000


def test_readonly_account_rejects_writes_and_multiple_statements(config):
    with read_connection(config) as connection:
        with connection.cursor() as cursor:
            # Even if a privilege regression occurs, WHERE FALSE cannot change data.
            with pytest.raises(pymysql.MySQLError):
                cursor.execute("UPDATE film SET title=title WHERE FALSE")
            with pytest.raises(pymysql.MySQLError):
                cursor.execute("SELECT 1; SELECT 2")


def test_safe_query_and_mysql_syntax_error_have_distinct_outcomes(config, tables):
    result = execute_sql(config, "SELECT COUNT(*) FROM film", tables)
    assert result.status == "success"
    assert result.result.rows == ((1000,),)
    error = execute_sql(config, "SELECT nonexistent_column FROM film", tables)
    assert error.status == "model_error"
    assert error.error_code == 1054
    rejected = execute_sql(config, "SELECT LOAD_FILE('/etc/passwd')", tables)
    assert rejected.status == "rejected"
    assert rejected.result is None


def test_server_query_deadline_is_enforced(config, tables):
    short = config.model_copy(update={"database": config.database.model_copy(update={"query_timeout_ms": 50})})
    # A pure COUNT over a Cartesian product can be optimized without enumeration.
    result = execute_sql(short, "SELECT SUM(a.rental_id*b.rental_id) FROM rental a CROSS JOIN rental b", tables)
    assert result.status == "model_error"
    assert result.error_code == 3024
    assert result.latency_ms < 5000


def test_result_limit_aborts_stream_and_next_query_still_works(config, tables):
    small = config.model_copy(update={"database": config.database.model_copy(update={"max_rows": 1})})
    result = execute_sql(small, "SELECT film_id FROM film ORDER BY film_id LIMIT 2", tables)
    assert result.status == "model_error"
    assert result.error_message == "result_resource_limit"
    assert execute_sql(config, "SELECT COUNT(*) FROM film", tables).result.rows == ((1000,),)


def test_connection_outage_is_infrastructure_not_model_error(config, tables):
    unavailable = config.model_copy(update={"database": config.database.model_copy(update={"port": 13307, "connect_timeout_s": 1})})
    result = execute_sql(unavailable, "SELECT COUNT(*) FROM film", tables)
    assert result.status == "infrastructure_error"
    assert result.result is None


def test_audit_remains_identical_after_execution_checks(config, inventory):
    verify_fingerprint(inspect_database(config), inventory)

