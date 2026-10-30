"""Reader-only connections with verified effective grants and fixed session settings."""

from __future__ import annotations

import re
from contextlib import contextmanager

import pymysql
from pymysql.constants import CLIENT

from ..config import AppConfig


class DatabasePolicyError(RuntimeError):
    pass


@contextmanager
def read_connection(config: AppConfig):
    settings = config.database
    connection = pymysql.connect(
        host=settings.host, port=settings.port, user=settings.username,
        password=config.database_password().get_secret_value(), database=settings.database,
        charset="utf8mb4", autocommit=True, local_infile=False,
        connect_timeout=settings.connect_timeout_s, read_timeout=settings.read_timeout_s,
        write_timeout=settings.connect_timeout_s, program_name="sakila-metadata-experiment",
    )
    try:
        if connection.client_flag & CLIENT.MULTI_STATEMENTS:
            raise DatabasePolicyError("Multi-statement execution must be disabled")
        with connection.cursor() as cursor:
            cursor.execute("SET SESSION time_zone=%s", (settings.time_zone,))
            cursor.execute("SET SESSION sql_mode=%s", (settings.sql_mode,))
            cursor.execute("SET SESSION max_execution_time=%s", (settings.query_timeout_ms,))
            if settings.time_names_locale is not None:
                cursor.execute("SET SESSION lc_time_names=%s", (settings.time_names_locale,))
                cursor.execute("SELECT @@session.lc_time_names")
                if cursor.fetchone() != (settings.time_names_locale,):
                    raise DatabasePolicyError("Database time-name locale differs from the configured experiment")
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            cursor.execute("SELECT CURRENT_USER(), @@global.read_only, @@global.super_read_only")
            account, read_only, super_read_only = cursor.fetchone()
            if account.split("@", 1)[0] != settings.username or not (read_only and super_read_only):
                raise DatabasePolicyError("The research database must be frozen and use the configured reader account")
            cursor.execute("SHOW GRANTS FOR CURRENT_USER")
            grants = [row[0] for row in cursor.fetchall()]
            usage = re.compile(r"^GRANT USAGE ON \*\.\* TO ")
            selection = re.compile(r"^GRANT SELECT ON `" + re.escape(settings.database) + r"`\.`[A-Za-z_][A-Za-z0-9_]*` TO ")
            if not grants or any(not (usage.match(grant) or selection.match(grant)) for grant in grants):
                raise DatabasePolicyError("Reader grants exceed SELECT on individual Sakila tables")
        yield connection
    finally:
        if connection.open:
            connection.close()

