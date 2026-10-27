import json
from dataclasses import asdict

import pytest

from sakila_experiment.analysis.report import IntegrityError, analyze_run, audit_run
from sakila_experiment.artifacts import canonical_json, publish_artifact, sha256_bytes
from sakila_experiment.config import ExperimentConfig
from sakila_experiment.contracts import Question
from sakila_experiment.experiment.ledger import Ledger
from sakila_experiment.experiment.schedule import build_schedule


def completed_fixture(directory, *, preliminary=False):
    question = Question(question_id="P001", question="Pertanyaan sintetis untuk pengujian audit?", complexity="simple")
    questions = tuple(Question(question_id=f"Q{i+1:03}", question=f"Pertanyaan sintetis nomor {i+1} untuk validasi?", complexity=("simple", "medium", "complex")[i // 10]) for i in range(30)) if preliminary else (question,)
    plan = build_schedule(questions, ExperimentConfig(), pilot=not preliminary)
    inference = {"temperature": .2}
    manifest = {"mode": "pilot_smoke", "experiment_id": "synthetic-test", "model_version_or_hash": "a" * 64,
                "inference_config": inference, "trial_plan_sha256": sha256_bytes(canonical_json([asdict(a) for a in plan])),
                "snapshots": {"snapshot_sha256": {s: "b" * 64 for s in ("S0", "S1", "S2", "S3")}}}
    if preliminary:
        manifest.update(mode="preliminary", main_experiment_allowed=False, allow_unreviewed=True, evaluation_status="provisional", gold_review_status=["draft"], experiment_config={"analysis_seed": 20261029})
    publish_artifact(directory / "manifest.json", canonical_json(manifest))
    publish_artifact(directory / "plan.json", canonical_json([asdict(a) for a in plan]))
    prompt_hash = publish_artifact(directory / "prompt.json", b"synthetic prompt\n")
    publish_artifact(directory / "prompts" / f"{prompt_hash}.json", b"synthetic prompt\n")
    gold_hash = publish_artifact(directory / "gold-results/P001.json", canonical_json({"column_count": 1, "rows": [[["number", "1"]]]}))
    for q in questions:
        publish_artifact(directory / "gold-results" / (q.question_id + ".json"), canonical_json({"column_count": 1, "rows": [[["number", "1"]]]}))
    rows = []
    with Ledger(directory / "ledger.sqlite3") as ledger:
        ledger.register("synthetic-test", manifest, plan)
        for assignment in plan:
            attempt = ledger.start_attempt("synthetic-test", assignment.trial_id)
            ledger.record_response("synthetic-test", assignment.trial_id, attempt, {"synthetic_fixture": True})
            row = {**asdict(assignment), "model_version_or_hash": "a" * 64, "inference_config": inference,
                   "snapshot_sha256": "b" * 64, "prompt_hash": prompt_hash, "gold_result_hash": gold_hash,
                   "execution_accuracy": 0, "execution_result_hash": None, "execution_status": "rejected", "extracted_sql": None,
                   "inference_latency_ms": 1.0, "sql_execution_latency_ms": None, "input_tokens": None, "output_tokens": None}
            ledger.finish_trial("synthetic-test", assignment.trial_id, attempt, row)
            rows.append(row)
        ledger.export_jsonl("synthetic-test", directory / "events.jsonl")
    publish_artifact(directory / "trials.jsonl", b"".join(canonical_json(row) for row in rows))
    publish_artifact(directory / "completion.json", canonical_json({"completed_trials": len(plan), "database_unchanged": True, "manifest_sha256": sha256_bytes(canonical_json(manifest))}))
    return directory


def test_complete_pilot_gets_descriptives_without_inferential_claims(tmp_path):
    directory = completed_fixture(tmp_path / "run")
    report = analyze_run(directory, tmp_path / "analysis")
    assert report["integrity_verified"] and not report["main_research_results"]
    assert "paired_analysis" not in report
    assert all(row["input_tokens"]["missing"] == 1 for row in report["descriptive"]["by_scenario"])


def test_duplicate_terminal_export_and_altered_gold_are_rejected(tmp_path):
    directory = completed_fixture(tmp_path / "run")
    path = directory / "trials.jsonl"
    path.chmod(0o644)
    original = path.read_bytes()
    path.write_bytes(original + original.splitlines(keepends=True)[0])
    with pytest.raises(IntegrityError, match="duplicate"):
        audit_run(directory)
    path.write_bytes(original)
    gold = directory / "gold-results/P001.json"
    gold.chmod(0o644)
    gold.write_bytes(b"changed result")
    with pytest.raises(IntegrityError, match="hash mismatch"):
        audit_run(directory)


def test_export_cannot_change_ex_even_when_trial_ids_remain_valid(tmp_path):
    directory = completed_fixture(tmp_path / "run")
    path = directory / "trials.jsonl"
    rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    rows[0]["execution_accuracy"] = 1
    path.chmod(0o644)
    path.write_bytes(b"".join(canonical_json(row) for row in rows))
    with pytest.raises(IntegrityError, match="ledger"):
        audit_run(directory)


def test_complete_preliminary_analysis_is_paired_and_marked_provisional(tmp_path):
    directory = completed_fixture(tmp_path / "run", preliminary=True)
    output = tmp_path / "analysis"
    report = analyze_run(directory, output)
    assert report["evaluation_status"] == "provisional" and report["main_research_results"] is False
    assert report["paired_analysis"]["question_count"] == 30
    assert all(r["trials"] == 150 for r in report["descriptive"]["by_scenario"])
    assert "provisional" in (output / "execution-accuracy.csv").read_text()
    assert "PROVISIONAL" in (output / "report.md").read_text()
    assert (output / "question-consistency.png").exists()
