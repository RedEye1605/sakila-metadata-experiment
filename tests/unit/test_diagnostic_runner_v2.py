import json
from dataclasses import replace
from pathlib import Path

import pytest

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.contracts import Question
from sakila_experiment.experiment import runner
from sakila_experiment.experiment.diagnostics import VARIANTS, diagnostic_schedule
from test_runner import setup_pilot


def test_diagnostic_freezes_sixty_prompts_and_resumes_without_regeneration(tmp_path, monkeypatch):
    config, snapshots, _, reference, _, _, calls = setup_pilot(tmp_path, monkeypatch)
    config = config.model_copy(update={"prompt_template": "prompts/revision.txt"})
    template = config.project_root / config.prompt_template
    template.write_text("Fixed diagnostic template; no gold enters this instruction.")
    questions = {f"P{i:03}": Question(question_id=f"P{i:03}", question=f"Berapa jumlah pemeran pada fixture {i}?", complexity="simple") for i in range(101, 113)}
    references = {qid: reference.model_copy(update={"question_id": qid}) for qid in questions}
    plan = diagnostic_schedule(tuple(questions.values()), config.experiment)
    directories = {}
    for variant in VARIANTS:
        folder = config.project_root / "diagnostic-contexts" / variant
        folder.mkdir(parents=True)
        for path in (snapshots / "S0").iterdir():
            (folder / path.name).write_bytes(path.read_bytes())
        directories[variant] = str(folder.relative_to(config.project_root))
    manifest = {"mode": "diagnostic", "evaluation_status": "provisional", "main_experiment_allowed": False,
                "prompt_template_sha256": sha256_bytes(template.read_bytes()), "diagnostic_rendering_directories": directories,
                "snapshot_manifest_sha256": {v: sha256_bytes((config.project_root / d / "manifest.json").read_bytes()) for v, d in directories.items()}}
    monkeypatch.setattr(runner, "_build_inputs", lambda *a, **k: (manifest.copy(), plan, questions, references))
    output = tmp_path / "diagnostic"
    with pytest.raises(runner.RunError, match="Freeze"):
        runner.run_diagnostic(config, snapshots, Path("unused"), output, "diagnostic", allow_unreviewed=True)
    assert not calls
    frozen = runner.run_diagnostic(config, snapshots, Path("unused"), output, "diagnostic", freeze_only=True, allow_unreviewed=True)
    assert frozen["trial_count"] == 180 and frozen["generation_requests"] == 0
    document = json.loads((output / "manifest.json").read_bytes())
    assert len(document["complete_diagnostic_prompt_budgets"]) == 60
    result = runner.run_diagnostic(config, snapshots, Path("unused"), output, "diagnostic", allow_unreviewed=True, progress=lambda _: None)
    assert result["status"] == "diagnostic_complete" and len(calls) == 180
    runner.run_diagnostic(config, snapshots, Path("unused"), output, "diagnostic", allow_unreviewed=True, progress=lambda _: None)
    assert len(calls) == 180
    rows = [json.loads(line) for line in (output / "trials.jsonl").read_bytes().splitlines()]
    assert {row["variant_id"] for row in rows} == set(VARIANTS)
    assert all(row["reference_review_status"] == "draft" for row in rows)
    assert all(row["prompt_hash"] and row["resolved_request_parameters"] is None for row in rows)


def test_diagnostic_cannot_enter_generation_without_versioned_instrument(tmp_path):
    from sakila_experiment.config import AppConfig
    with pytest.raises(runner.RunError, match="versioned exploratory instrument"):
        runner._build_inputs(AppConfig(project_root=tmp_path), tmp_path, tmp_path / "backend", mode="diagnostic", allow_unreviewed=True)
    assert not list(tmp_path.iterdir())
