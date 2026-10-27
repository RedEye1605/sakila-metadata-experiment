import json
from types import SimpleNamespace

import pytest

from sakila_experiment.resources import pause_authorized_airflow


def test_paused_services_are_restored_on_failure(tmp_path, monkeypatch):
    calls = []

    def run(arguments, **kwargs):
        calls.append(arguments)
        if arguments[1] == "ps":
            return SimpleNamespace(stdout=json.dumps({"ID": "authorized-id", "Names": "airflow-existing"}))
        return SimpleNamespace(stdout="")

    monkeypatch.setattr("sakila_experiment.resources.subprocess.run", run)
    monkeypatch.setattr("sakila_experiment.resources.memory_available_bytes", lambda: 100)
    with pytest.raises(RuntimeError):
        with pause_authorized_airflow(tmp_path):
            raise RuntimeError("Simulated metadata failure")
    assert calls[-1] == ["docker", "start", "authorized-id"]
    assert (tmp_path / "before.json").exists()
    assert (tmp_path / "restored.json").exists()

