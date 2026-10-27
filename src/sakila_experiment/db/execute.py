"""Bounded execution of untrusted SQL using reader credentials only."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import pymysql
from pymysql.cursors import SSCursor

from ..artifacts import canonical_json, sha256_bytes
from ..config import AppConfig, ConfigurationError
from ..evaluation.safety import validate_sql
from .connection import DatabasePolicyError, read_connection
from .values import encode_row

INFRASTRUCTURE_CODES = frozenset({1040, 1042, 1045, 1046, 1049, 1053, 1037, 1038, 1142, 1317, 2002, 2003, 2006, 2013})


@dataclass(frozen=True)
class ResultTable:
    columns: tuple[str, ...]
    type_codes: tuple[int, ...]
    rows: tuple[tuple, ...]

    def encoded(self) -> dict:
        return {"column_count": len(self.columns), "rows": [encode_row(row) for row in self.rows]}


@dataclass(frozen=True)
class QueryExecution:
    status: str
    validation_code: str
    result: ResultTable | None = None
    result_sha256: str | None = None
    latency_ms: float | None = None
    error_code: int | None = None
    error_message: str | None = None


def _abort_stream(cursor: SSCursor, connection) -> None:
    """Disconnect without draining arbitrary results (pinned PyMySQL 1.2.3).

    SSCursor.close() normally drains all remaining rows. On a resource limit,
    close the socket and detach the result so its destructor cannot drain it.
    The server SELECT deadline remains an independent backstop.
    """
    connection.close()
    if cursor._result is not None:
        cursor._result.unbuffered_active = False
        cursor._result.connection = None
    cursor.connection = None


def execute_sql(config: AppConfig, sql: str, tables: frozenset[str]) -> QueryExecution:
    validation = validate_sql(sql, tables, config.database.database)
    if not validation.accepted:
        return QueryExecution("rejected", validation.code)
    started = None
    try:
        with read_connection(config) as connection:
            cursor = connection.cursor(SSCursor)
            try:
                started = perf_counter()
                cursor.execute(sql)
                columns = tuple(column[0] for column in cursor.description or ())
                codes = tuple(column[1] for column in cursor.description or ())
                rows = []
                size = 0
                while True:
                    row = cursor.fetchone()
                    if row is None:
                        break
                    size += len(canonical_json(encode_row(row)))
                    if len(rows) >= config.database.max_rows or size > config.database.max_result_bytes:
                        _abort_stream(cursor, connection)
                        return QueryExecution("model_error", "accepted", latency_ms=(perf_counter() - started) * 1000, error_message="result_resource_limit")
                    rows.append(tuple(row))
                latency = (perf_counter() - started) * 1000
                result = ResultTable(columns, codes, tuple(rows))
                return QueryExecution("success", "accepted", result, sha256_bytes(canonical_json(result.encoded())), latency)
            except BaseException:
                _abort_stream(cursor, connection)
                raise
            finally:
                if cursor.connection is not None:
                    cursor.close()
    except pymysql.MySQLError as exc:
        code = exc.args[0] if exc.args and isinstance(exc.args[0], int) else None
        status = "infrastructure_error" if started is None or code in INFRASTRUCTURE_CODES else "model_error"
        return QueryExecution(status, "accepted", latency_ms=(perf_counter() - started) * 1000 if started is not None else None, error_code=code, error_message=str(exc))
    except (ConfigurationError, DatabasePolicyError, OSError, TypeError, ValueError):
        return QueryExecution("infrastructure_error", "accepted", error_message="database_configuration_policy_or_value_error")

