from pathlib import Path

import pytest

from sakila_experiment.config import ConfigurationError, load_config


def config_file(tmp_path, text=""):
    path = tmp_path / "config.toml"
    path.write_text('project_root = "."\n' + text)
    return path


def test_config_paths_are_relative_to_file_not_working_directory(tmp_path, monkeypatch):
    path = config_file(tmp_path)
    monkeypatch.chdir("/")
    config = load_config(path)
    assert config.project_root == tmp_path
    assert config.resolve("secrets/reader.txt") == tmp_path / "secrets/reader.txt"


@pytest.mark.parametrize("text", [
    '[database]\nusername="root"',
    '[database]\nport=0',
    '[database]\nread_timeout_s=1',
    '[experiment]\nrepetitions=6',
    '[experiment]\nscenario_ids=["S0","S2","S1","S3"]',
    '[inference]\ntemperature=0',
    '[inference]\ncontext_tokens=1024',
])
def test_invalid_or_unapproved_configuration_fails(tmp_path, text):
    with pytest.raises(ConfigurationError):
        load_config(config_file(tmp_path, text))


@pytest.mark.parametrize("text", [
    '[database]\npassword="highly-sensitive-value"',
    '[inference]\nbase_url="http://user:highly-sensitive-value@127.0.0.1:18081"',
    '[database]\nport="highly-sensitive-value"',
])
def test_invalid_config_never_displays_input_values(tmp_path, text):
    with pytest.raises(ConfigurationError) as caught:
        load_config(config_file(tmp_path, text))
    assert "highly-sensitive-value" not in str(caught.value)


def test_password_resolution_prefers_environment_without_serializing_it(tmp_path, monkeypatch):
    config = load_config(config_file(tmp_path))
    secret_file = config.resolve("secrets/reader_password.txt")
    secret_file.parent.mkdir()
    secret_file.write_text("file-secret")
    monkeypatch.setenv("SAKILA_READER_PASSWORD", "environment-secret")
    assert config.database_password().get_secret_value() == "environment-secret"
    assert "environment-secret" not in config.model_dump_json()


def test_password_missing_is_safe(tmp_path, monkeypatch):
    monkeypatch.delenv("SAKILA_READER_PASSWORD", raising=False)
    with pytest.raises(ConfigurationError):
        load_config(config_file(tmp_path)).database_password()

