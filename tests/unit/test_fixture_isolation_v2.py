import json

import pytest

from sakila_experiment.config import AppConfig
from sakila_experiment.evaluation.fixtures import FIXTURE_PORT, FixtureError, assert_fixture_topology, fixture_config, setup_fixture_database, fixture_setup_sql


def test_primary_database_can_never_pass_fixture_mutation_guard(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Guard must reject before any Docker/admin call")
    monkeypatch.setattr("sakila_experiment.evaluation.fixtures.run_command", forbidden)
    with pytest.raises(FixtureError, match="restricted"):
        assert_fixture_topology(AppConfig(project_root=tmp_path))


def test_clone_name_is_insufficient_without_credential_mount_and_loopback_port(tmp_path, monkeypatch):
    config = fixture_config(tmp_path)
    invalid = [{"Mounts": [{"Destination": "/run/secrets/admin_client", "Source": "/primary/secrets/admin-client.cnf"}],
                "NetworkSettings": {"Ports": {"3306/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(FIXTURE_PORT)}]}}}]
    monkeypatch.setattr("sakila_experiment.evaluation.fixtures.run_command", lambda *args, **kwargs: json.dumps(invalid).encode())
    with pytest.raises(FixtureError, match="credentials"):
        assert_fixture_topology(config)


def test_only_exact_isolated_topology_passes(tmp_path, monkeypatch):
    config = fixture_config(tmp_path)
    valid = [{"Mounts": [{"Destination": "/run/secrets/admin_client", "Source": str(config.resolve("secrets/admin-client.cnf"))}],
              "NetworkSettings": {"Ports": {"3306/tcp": [{"HostIp": "127.0.0.1", "HostPort": str(FIXTURE_PORT)}]}}}]
    monkeypatch.setattr("sakila_experiment.evaluation.fixtures.run_command", lambda *args, **kwargs: json.dumps(valid).encode())
    assert_fixture_topology(config)


def test_fixture_setup_renders_expected_container_project_and_port(tmp_path, monkeypatch):
    (tmp_path / "infra").mkdir()
    (tmp_path / "downloads/sakila").mkdir(parents=True)
    (tmp_path / "infra/compose.yaml").write_text("name: sakila-research\nservices:\n  mysql:\n    container_name: sakila-research-mysql\n    ports:\n      - 127.0.0.1:13306:3306\n")
    calls = []
    monkeypatch.setattr("sakila_experiment.evaluation.fixtures.bootstrap_database", lambda *args, **kwargs: calls.append(kwargs))
    monkeypatch.setattr("sakila_experiment.evaluation.fixtures.assert_fixture_topology", lambda *args: None)
    config = setup_fixture_database(tmp_path)
    rendered = config.resolve("infra/compose.yaml").read_text()
    assert "name: sakila-revision02-fixtures\n" in rendered
    assert "container_name: sakila-repro-revision02-fixtures-mysql" in rendered
    assert "127.0.0.1:13311:3306" in rendered
    assert calls == [{"container_name": "sakila-repro-revision02-fixtures-mysql"}]


def test_fixture_event_rows_keep_distinct_dates_under_installed_insert_triggers():
    from sqlglot import exp, parse
    from datetime import datetime, timezone
    script = fixture_setup_sql(["INSERT INTO sakila.rental(rental_id,rental_date,inventory_id,customer_id,staff_id) VALUES(1,'2005-07-01 00:00:00',1,1,1),(2,'2005-07-08 00:00:00',1,1,1)"], 1120176000)
    statements = parse(script, read="mysql")
    inserts = [tree for tree in statements if isinstance(tree, exp.Insert)]
    assert len(inserts) == 2
    assert all(len(tree.expression.expressions) == 1 for tree in inserts)
    for tree in inserts:
        literal = tree.expression.expressions[0].expressions[1].this
        timestamp = int(datetime.fromisoformat(literal).replace(tzinfo=timezone.utc).timestamp())
        assert f"SET SESSION timestamp={timestamp};\n{tree.sql(dialect='mysql')}" in script
    assert "TRIGGER" not in script and "FOREIGN_KEY_CHECKS" not in script
