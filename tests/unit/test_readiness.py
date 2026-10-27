import json
from pathlib import Path

import pytest

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.config import AppConfig, InferenceConfig
from sakila_experiment.analysis.report import IntegrityError
from sakila_experiment.experiment import readiness


@pytest.fixture
def case(tmp_path, monkeypatch):
    def write(name, value):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json(value) if not isinstance(value, bytes) else value)
        return path
    for scope, prefix, count in (("main", "Q", 30), ("pilot", "P", 9)):
        questions = [{"question_id": f"{prefix}{i:03}", "question": f"Pertanyaan {scope} sintetis nomor {i}?", "complexity": ("simple", "medium", "complex")[(i - 1) // (count // 3)]} for i in range(1, count + 1)]
        references = [{"question_id": q["question_id"], "sql": "SELECT 1", "column_count": 1, "review_status": "approved"} for q in questions]
        write("data/public/main.questions.jsonl" if scope == "main" else "data/pilot/questions.jsonl", b"".join(canonical_json(q) for q in questions))
        write("data/private/main.gold.jsonl" if scope == "main" else "data/pilot/gold.jsonl", b"".join(canonical_json(q) for q in references))
    write("data/annotations/specification.json", {})
    write("data/reviews/decisions.json", {"decisions": []})
    for file in ("docs/analysis-plan.md", "docs/evaluation-protocol.md", "src/sakila_experiment/analysis/statistics.py", "prompts/generation.txt"):
        write(file, b"synthetic fixture\n")
    critical = ("generation/llama.py", "generation/prompt.py", "db/connection.py", "db/execute.py", "evaluation/compare.py", "evaluation/safety.py", "experiment/runner.py", "experiment/schedule.py")
    sources = []
    for name in critical:
        path = write("src/sakila_experiment/" + name, b"synthetic fixture\n")
        sources.append({"path": str(path.relative_to(tmp_path)), "sha256": sha256_bytes(path.read_bytes())})
    snapshots = tmp_path / "snapshots"
    summary = {"snapshot_sha256": {s: "b" * 64 for s in ("S0", "S1", "S2", "S3")}}
    for scenario in summary["snapshot_sha256"]:
        write(f"snapshots/{scenario}/manifest.json", {"scenario_id": scenario, "database_schema_sha256": "c" * 64})
    monkeypatch.setattr(readiness, "validate_scenario_set", lambda p: summary)
    backend = write("backend.json", {"model_sha256": "a" * 64})
    write("runs/database/baseline.json", {"schema_sha256": "c" * 64, "data_sha256": "d" * 64})
    config = AppConfig(project_root=tmp_path, inference=InferenceConfig(model_id="fixture"))
    manifest = {"mode": "pilot", "inference_config": config.inference.model_dump(mode="json"), "model_version_or_hash": "a" * 64,
                "backend_evidence_sha256": sha256_bytes(backend.read_bytes()), "prompt_template_sha256": sha256_bytes((tmp_path / "prompts/generation.txt").read_bytes()),
                "snapshots": summary, "questions_sha256": sha256_bytes((tmp_path / "data/pilot/questions.jsonl").read_bytes()),
                "gold_sha256": sha256_bytes((tmp_path / "data/pilot/gold.jsonl").read_bytes()), "database_schema_sha256": "c" * 64, "database_data_sha256": "d" * 64,
                "source_version": {"source_files": sources}}
    pilot = tmp_path / "pilot"
    write("pilot/manifest.json", manifest)
    write("pilot/completion.json", {"mode": "pilot", "completed_trials": 36})
    write("sampler-verification.json", {"status": "sampler_seed_cache_verified", "model_sha256": "a" * 64,
                                       "backend_evidence_sha256": sha256_bytes(backend.read_bytes()), "pilot_manifest_sha256": sha256_bytes((pilot / "manifest.json").read_bytes())})
    rows = [{"question_id": f"P{i:03}", "scenario_id": s, "repetition_id": 1} for i in range(1, 10) for s in ("S0", "S1", "S2", "S3")]
    monkeypatch.setattr(readiness, "audit_run", lambda p: (manifest, rows))
    return config, snapshots, backend, pilot, manifest, rows


def test_machine_checks_do_not_create_human_approvals(case):
    config, snapshots, backend, pilot, manifest, rows = case
    result = readiness.main_readiness(config, snapshots, backend, pilot)
    assert result["status"] == "blocked"
    assert all(c["status"] == "passed" for c in result["automated_checks"])
    assert {r["component"] for r in result["required_reviews"]} == {"benchmark", "metadata", "generation", "analysis"}
    assert all(r["review_status"] == "pending" for r in result["required_reviews"])
    assert json.loads((config.project_root / "data/reviews/decisions.json").read_bytes())["decisions"] == []


def test_changed_model_or_truncated_pilot_fails_even_with_completion_receipt(case):
    config, snapshots, backend, pilot, manifest, rows = case
    manifest["model_version_or_hash"] = "e" * 64
    rows.pop()
    result = readiness.main_readiness(config, snapshots, backend, pilot)
    assert {c["check"] for c in result["automated_checks"] if c["status"] == "failed"} >= {"pilot_configuration", "pilot_completeness"}


def test_bad_integrity_and_changed_runtime_are_reported(case, monkeypatch):
    config, snapshots, backend, pilot, manifest, rows = case
    (config.project_root / "src/sakila_experiment/generation/llama.py").write_text("changed")
    result = readiness.main_readiness(config, snapshots, backend, pilot)
    assert any(c["check"] == "pilot_runtime_source" and c["status"] == "failed" for c in result["automated_checks"])
    def broken(p): raise IntegrityError("fixture corruption")
    monkeypatch.setattr(readiness, "audit_run", broken)
    result = readiness.main_readiness(config, snapshots, backend, pilot)
    assert any(c["check"] == "pilot_integrity" and c["status"] == "failed" for c in result["automated_checks"])
