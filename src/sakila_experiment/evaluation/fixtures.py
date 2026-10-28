"""Administrative fixture builder, restricted to one separately verified clone.

Never imported by the inference client or untrusted-SQL executor. Builder SQL is
trusted, source-controlled research setup; predictions still use the reader.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlglot import exp, parse_one

from ..artifacts import canonical_json, publish_artifact, sha256_bytes
from ..bootstrap import admin_sql, bootstrap_database, run_command
from ..config import AppConfig
from ..db.inspect import inspect_database

FIXTURE_CONTAINER = "sakila-repro-revision02-fixtures-mysql"
FIXTURE_PORT = 13311


class FixtureError(RuntimeError):
    pass


def fixture_setup_sql(statements: list[str], fixed_timestamp: int) -> str:
    """Honor installed BEFORE INSERT date triggers using per-row server time.

    Rental/payment date triggers are in the official DATA file. They must not
    be removed or disabled to populate a counterexample. Every setup event is
    inserted separately with a deterministic session timestamp matching its
    declared event date. This transforms trusted setup only, never predictions.
    """
    if type(fixed_timestamp) is not int or fixed_timestamp <= 0:
        raise FixtureError("Fixture session timestamp is invalid")
    lines = ["SET SESSION time_zone='+00:00'", f"SET SESSION timestamp={fixed_timestamp}"]
    trigger_dates = {"customer": "create_date", "payment": "payment_date", "rental": "rental_date"}
    for statement in statements:
        tree = parse_one(statement, read="mysql")
        if isinstance(tree, exp.Insert) and isinstance(tree.this, exp.Schema):
            table = tree.this.this
            columns = [column.name for column in tree.this.expressions]
            date_column = trigger_dates.get(table.name)
            if date_column and date_column in columns:
                values = tree.expression
                if not isinstance(values, exp.Values):
                    raise FixtureError("Event setup requires explicit bounded VALUES")
                for row in values.expressions:
                    literal = row.expressions[columns.index(date_column)]
                    if not isinstance(literal, exp.Literal) or not literal.is_string:
                        raise FixtureError("Fixture event date must be a literal UTC date/time")
                    date = datetime.fromisoformat(literal.this)
                    if date.tzinfo is not None:
                        raise FixtureError("Fixture event dates must use naive stored UTC components")
                    timestamp = int(date.replace(tzinfo=timezone.utc).timestamp())
                    single = tree.copy()
                    single.set("expression", exp.Values(expressions=[row.copy()]))
                    lines.extend([f"SET SESSION timestamp={timestamp}", single.sql(dialect="mysql")])
                lines.append(f"SET SESSION timestamp={fixed_timestamp}")
                continue
        lines.append(statement)
    return ";\n".join(lines) + ";"


def fixture_config(root: Path) -> AppConfig:
    workspace = root.resolve() / "runs/revision-02/fixture-workspace"
    return AppConfig(project_root=workspace, database={"port": FIXTURE_PORT})


def assert_fixture_topology(config: AppConfig):
    if (config.database.host != "127.0.0.1" or config.database.port != FIXTURE_PORT
            or config.database.database != "sakila" or config.project_root.name != "fixture-workspace"
            or config.project_root.parent.name != "revision-02"):
        raise FixtureError("Fixture mutation is restricted to the revision-02 clone workspace")
    inspection = json.loads(run_command(["docker", "inspect", FIXTURE_CONTAINER]))[0]
    port = inspection["NetworkSettings"]["Ports"].get("3306/tcp", [])
    mounts = [m for m in inspection["Mounts"] if m["Destination"] == "/run/secrets/admin_client"]
    if (port != [{"HostIp": "127.0.0.1", "HostPort": str(FIXTURE_PORT)}] or len(mounts) != 1
            or Path(mounts[0]["Source"]).resolve() != config.resolve("secrets/admin-client.cnf")):
        raise FixtureError("Fixture container does not match the isolated credentials and port")


def setup_fixture_database(root: Path) -> AppConfig:
    root = root.resolve()
    config = fixture_config(root)
    workspace = config.project_root
    compose = workspace / "infra/compose.yaml"
    if not compose.exists():
        compose.parent.mkdir(parents=True, exist_ok=True)
        content = (root / "infra/compose.yaml").read_text()
        content = content.replace("name: sakila-research\n", "name: sakila-revision02-fixtures\n", 1)
        content = content.replace("container_name: sakila-research-mysql", "container_name: " + FIXTURE_CONTAINER)
        content = content.replace("127.0.0.1:13306:3306", f"127.0.0.1:{FIXTURE_PORT}:3306")
        compose.write_text(content)
        shutil.copytree(root / "downloads/sakila", workspace / "downloads/sakila")
    bootstrap_database(config, container_name=FIXTURE_CONTAINER)
    assert_fixture_topology(config)
    return config


def prepare_fixture(root: Path, fixture_id: str, output: Path) -> tuple[AppConfig, dict]:
    definition = root / "research/revision-02/fixture_cases.json"
    cases = json.loads(definition.read_bytes())
    selected = [case for case in cases["cases"] if case["fixture_id"] == fixture_id]
    if len(selected) != 1:
        raise FixtureError("Unknown or duplicate fixture case")
    if output.exists():
        raise FixtureError("Fixture receipt output must be new")
    config = setup_fixture_database(root)
    assert_fixture_topology(config)
    source = config.resolve("downloads/sakila")
    try:
        admin_sql("SET GLOBAL super_read_only=OFF; SET GLOBAL read_only=OFF; DROP DATABASE sakila;", FIXTURE_CONTAINER)
        admin_sql((source / "sakila-schema.sql").read_bytes(), FIXTURE_CONTAINER)
        admin_sql((source / "sakila-data.sql").read_bytes(), FIXTURE_CONTAINER)
        timestamp = cases["fixed_session_timestamp"]
        sql = fixture_setup_sql(selected[0]["sql"], timestamp)
        admin_sql(sql, FIXTURE_CONTAINER)
    finally:
        admin_sql("SET PERSIST read_only=ON; SET PERSIST super_read_only=ON;", FIXTURE_CONTAINER)
    actual = inspect_database(config)
    baseline = json.loads((root / "runs/database/baseline.json").read_bytes())
    # Data differ intentionally. The full installed schema/FKs must not change.
    if actual["schema_sha256"] != baseline["schema_sha256"]:
        raise FixtureError("Fixture changed the installed technical schema")
    report = {"fixture_id": fixture_id, "fixture_definition_sha256": sha256_bytes(definition.read_bytes()),
              "case_sha256": sha256_bytes(canonical_json(selected[0])), "fixed_session_timestamp": timestamp,
              "database_schema_sha256": actual["schema_sha256"], "database_data_sha256": actual["data_sha256"],
              "container": FIXTURE_CONTAINER, "port": FIXTURE_PORT, "reader_only_execution": True,
              "installed_date_triggers_preserved": True, "setup_sql_sha256": sha256_bytes(sql.encode()),
              "primary_database_modified": False, "human_review_complete": False, "generation_requests": 0}
    publish_artifact(output, canonical_json(report))
    return config, report
