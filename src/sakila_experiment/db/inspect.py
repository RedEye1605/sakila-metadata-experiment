"""Installed-schema inventory and full-content fingerprints, never model context."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from pymysql.cursors import DictCursor, SSCursor

from ..artifacts import canonical_json, sha256_bytes
from ..config import AppConfig
from .connection import DatabasePolicyError, read_connection
from .values import encode_row


def quote_identifier(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"


def inspect_database(config: AppConfig) -> dict:
    database = config.database.database
    with read_connection(config) as connection:
        with connection.cursor(DictCursor) as cursor:
            cursor.execute("SELECT VERSION() AS version, @@session.sql_mode AS sql_mode, @@session.time_zone AS time_zone, @@character_set_database AS character_set, @@collation_database AS collation, @@global.read_only AS read_only, @@global.super_read_only AS super_read_only")
            server = cursor.fetchone()
            cursor.execute("SELECT TABLE_NAME AS name, TABLE_TYPE AS object_type, ENGINE AS engine FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s ORDER BY TABLE_NAME", (database,))
            objects = list(cursor.fetchall())
            tables = [dict(item, columns=[], primary_key=[], foreign_keys=[]) for item in objects if item["object_type"] == "BASE TABLE"]
            by_name = {table["name"]: table for table in tables}
            if not tables:
                raise DatabasePolicyError("No installed research base tables were found")
            if any(table["engine"] != "InnoDB" for table in tables):
                raise DatabasePolicyError("Non-InnoDB base tables require a reviewed consistency policy")
            cursor.execute("SELECT TABLE_NAME AS table_name, COLUMN_NAME AS name, COLUMN_TYPE AS data_type, IS_NULLABLE AS is_nullable, ORDINAL_POSITION AS ordinal_position FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s ORDER BY TABLE_NAME, ORDINAL_POSITION", (database,))
            for column in cursor.fetchall():
                table = by_name.get(column["table_name"])
                if table is not None:
                    table["columns"].append({"name": column["name"], "data_type": column["data_type"], "nullable": column["is_nullable"] == "YES", "ordinal_position": column["ordinal_position"]})
            cursor.execute("SELECT TABLE_NAME AS table_name, COLUMN_NAME AS column_name, ORDINAL_POSITION AS ordinal_position FROM information_schema.KEY_COLUMN_USAGE WHERE CONSTRAINT_SCHEMA=%s AND CONSTRAINT_NAME='PRIMARY' ORDER BY TABLE_NAME,ORDINAL_POSITION", (database,))
            for key in cursor.fetchall():
                if key["table_name"] in by_name:
                    by_name[key["table_name"]]["primary_key"].append(key["column_name"])
            cursor.execute("SELECT k.TABLE_NAME AS table_name,k.CONSTRAINT_NAME AS name,k.COLUMN_NAME AS source_column,k.REFERENCED_TABLE_SCHEMA AS target_schema,k.REFERENCED_TABLE_NAME AS target_table,k.REFERENCED_COLUMN_NAME AS target_column,k.ORDINAL_POSITION AS position,r.UPDATE_RULE AS update_rule,r.DELETE_RULE AS delete_rule FROM information_schema.KEY_COLUMN_USAGE k JOIN information_schema.REFERENTIAL_CONSTRAINTS r ON k.CONSTRAINT_SCHEMA=r.CONSTRAINT_SCHEMA AND k.CONSTRAINT_NAME=r.CONSTRAINT_NAME AND k.TABLE_NAME=r.TABLE_NAME WHERE k.CONSTRAINT_SCHEMA=%s AND k.REFERENCED_TABLE_NAME IS NOT NULL ORDER BY k.TABLE_NAME,k.CONSTRAINT_NAME,k.ORDINAL_POSITION", (database,))
            foreign_keys = {}
            for key in cursor.fetchall():
                identity = (key["table_name"], key["name"])
                if identity not in foreign_keys:
                    record = {"name": key["name"], "source_columns": [], "target_schema": key["target_schema"], "target_table": key["target_table"], "target_columns": [], "update_rule": key["update_rule"], "delete_rule": key["delete_rule"]}
                    foreign_keys[identity] = record
                    by_name[key["table_name"]]["foreign_keys"].append(record)
                foreign_keys[identity]["source_columns"].append(key["source_column"])
                foreign_keys[identity]["target_columns"].append(key["target_column"])
        content = []
        ddl = {}
        for table in tables:
            name = table["name"]
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW CREATE TABLE {quote_identifier(database)}.{quote_identifier(name)}")
                ddl[name] = cursor.fetchone()[1]
            query = f"SELECT * FROM {quote_identifier(database)}.{quote_identifier(name)}"
            if table["primary_key"]:
                query += " ORDER BY " + ",".join(map(quote_identifier, table["primary_key"]))
            digest = hashlib.sha256()
            digest.update(canonical_json({"columns": [column["name"] for column in table["columns"]]}))
            count = 0
            unordered_hashes = []
            with connection.cursor(SSCursor) as cursor:
                cursor.execute(query)
                for row in cursor:
                    serialized = canonical_json(encode_row(row))
                    if table["primary_key"]:
                        digest.update(serialized)
                    else:
                        unordered_hashes.append(sha256_bytes(serialized))
                    count += 1
            if unordered_hashes:
                digest.update(canonical_json(sorted(unordered_hashes)))
            content.append({"table": name, "row_count": count, "sha256": digest.hexdigest()})
    technical = {"database": database, "tables": tables}
    return {
        "report_schema_version": 1, "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "server": server, "objects": objects, "technical_schema": technical,
        "schema_sha256": sha256_bytes(canonical_json(technical)),
        "ddl_sha256": sha256_bytes(canonical_json(ddl)),
        "data_sha256": sha256_bytes(canonical_json(content)), "table_content": content,
        "scope_note": "Installed base-table audit; this direct MySQL report is not an MCP-retrieved scenario snapshot",
    }


def verify_fingerprint(actual: dict, baseline: dict) -> None:
    keys = ("schema_sha256", "ddl_sha256", "data_sha256", "server")
    if any(actual[key] != baseline[key] for key in keys):
        raise DatabasePolicyError("Database content, schema, or session settings differ from the frozen baseline")

