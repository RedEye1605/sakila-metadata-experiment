import json

from sakila_experiment.cli import main
from sakila_experiment.config import load_config
from sakila_experiment.doctor import inspect_environment


def test_report_never_includes_secret_environment(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    config_path.write_text('project_root="."')
    monkeypatch.setenv("SAKILA_READER_PASSWORD", "private-reader-password")
    monkeypatch.setenv("DATAHUB_GMS_TOKEN", "private-catalog-token")
    monkeypatch.setattr("sakila_experiment.doctor.command_probe", lambda args: {"status": "unavailable"})
    report = inspect_environment(load_config(config_path), services=False)
    serialized = json.dumps(report)
    assert "private-reader-password" not in serialized
    assert "private-catalog-token" not in serialized
    assert "services" not in report
    assert report["readiness"]["main_experiment_ready"] is False


def test_cli_reports_configuration_errors_without_secrets(tmp_path, capsys):
    path = tmp_path / "bad.toml"
    path.write_text('[database]\npassword="never-print-this"')
    assert main(["doctor", "--config", str(path), "--offline"]) == 2
    output = capsys.readouterr()
    assert "never-print-this" not in output.out + output.err
    assert "Invalid configuration" in output.err

