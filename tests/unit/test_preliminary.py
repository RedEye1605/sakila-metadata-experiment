from pathlib import Path

import pytest

from sakila_experiment.config import AppConfig
from sakila_experiment.experiment import runner
from test_runner import setup_pilot


def test_preliminary_requires_opt_in_before_reading_inputs(tmp_path):
    with pytest.raises(runner.RunError, match="explicit"):
        runner._build_inputs(AppConfig(project_root=tmp_path), tmp_path, tmp_path / "backend", mode="preliminary_pilot")
    assert list(tmp_path.iterdir()) == []


def test_opt_in_pilot_preserves_draft_status_and_resume(tmp_path, monkeypatch):
    config, snapshots, assignments, reference, success, response, calls = setup_pilot(tmp_path, monkeypatch)
    def provisional(*args, **kwargs):
        assert kwargs["allow_unreviewed"] is True
        manifest, plan, questions, references = runner.pilot_inputs(config, snapshots, Path("unused"))
        manifest.update(mode="preliminary_pilot", evaluation_status="provisional", allow_unreviewed=True, main_experiment_allowed=False)
        return manifest, plan, questions, references
    monkeypatch.setattr(runner, "_build_inputs", provisional)
    output = tmp_path / "preliminary"
    result = runner.run_preliminary(config, snapshots, Path("unused"), output, "fixture", pilot=True, allow_unreviewed=True, progress=lambda _: None)
    assert result["status"] == "preliminary_complete" and result["main_experiment_allowed"] is False
    runner.run_preliminary(config, snapshots, Path("unused"), output, "fixture", pilot=True, allow_unreviewed=True, progress=lambda _: None)
    assert len(calls) == 4 and reference.review_status == "draft"
