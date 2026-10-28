import importlib.util
import json
from pathlib import Path

import pytest

from sakila_experiment.analysis.report import descriptive
from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.config import AppConfig
from sakila_experiment.contracts import load_questions
from sakila_experiment.experiment.schedule import build_schedule

ROOT = Path(__file__).parents[2]


def fixture(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("thesis_writer_test", ROOT / "research/revision-03/write_thesis.py")
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    root = tmp_path / "project";run = root / "runs/synthetic";run.mkdir(parents=True)
    questions_path = ROOT / "data/benchmarks/revision-03/final-02/questions.jsonl"
    questions = load_questions(questions_path);config = AppConfig()
    plan = build_schedule(questions, config.experiment)
    rows = [{**r.__dict__, "execution_accuracy": 0, "execution_status": "rejected", "validation_status": "synthetic",
             "error_type": "synthetic_only", "execution_error_code": None, "extracted_sql": None,
             "inference_latency_ms": 1, "sql_execution_latency_ms": None, "input_tokens": None, "output_tokens": None,
             "timestamp": "2026-10-29T00:00:00Z"} for r in plan]
    baseline = {"technical_schema": {"tables": [{"name": "actor", "columns": [{"name": "actor_id", "data_type": "int"}], "primary_key": ["actor_id"], "foreign_keys": []}]},
                "table_content": [{"table": "actor", "row_count": 2}], "server": {"character_set": "utf8mb4", "collation": "utf8mb4_0900_ai_ci"}}
    (root / "runs/database").mkdir();(root / "runs/database/baseline.json").write_bytes(canonical_json(baseline))
    manifest = {"mode": "main", "experiment_id": "synthetic-only-not-a-research-result", "instrument_paths": {
        "questions": str(questions_path), "gold": str(ROOT / "data/benchmarks/revision-03/final-02/gold.jsonl")},
        "backend_evidence": {"model_repository": "synthetic", "model_repository_revision": "synthetic", "quantization_runtime": "synthetic", "build_info": "synthetic", "gpu_layers": 0},
        "inference_config": config.inference.model_dump(), "experiment_config": config.experiment.model_dump(),
        "review_attestation": {"recorded_at_utc": "2026-10-29T00:00:00Z"},
        "source_version": {"git_commit": "synthetic", "source_tree_sha256": "a" * 64},
        "snapshots": {"snapshot_sha256": {s: "b" * 64 for s in config.experiment.scenario_ids}},
        "python_version": "synthetic", "mysql_version": "synthetic", "package_versions": {},
        "model_version_or_hash": "c" * 64, "database_schema_sha256": "d" * 64, "database_data_sha256": "e" * 64,
        "database_config": config.database.model_dump(), "comparator_version": "ex-results-v3-column-permutation"}
    monkeypatch.setattr(module, "audit_run", lambda _: (manifest, rows))
    (run / "benchmark").mkdir();(run / "benchmark/manifest.json").write_bytes(canonical_json(manifest))
    (run / "analysis").mkdir();(run / "auxiliary").mkdir()
    report = {"integrity_verified": True, "experiment_id": manifest["experiment_id"], "descriptive": descriptive(rows),
              "paired_analysis": {"omnibus": {"p_value": 1}, "seed": 1, "contrasts": []},
              "infrastructure_accounting": {"request_attempts_started": 600, "infrastructure_incidents": 0, "incident_types": {}}}
    (run / "analysis/report.json").write_bytes(canonical_json(report))
    (run / "auxiliary/report.json").write_bytes(canonical_json({"status": "auxiliary_replay_complete"}))
    cases = [f"synthetic-{i}" for i in range(8)]
    (run / "auxiliary/plan.json").write_bytes(canonical_json({"case_ids": cases, "source_run_manifest_sha256": sha256_bytes((run / "benchmark/manifest.json").read_bytes())}))
    aux = [{"trial_id": r["trial_id"], "fixture_id": c, "execution_accuracy": 0} for r in rows for c in cases]
    (run / "auxiliary/outcomes.jsonl").write_bytes(b"".join(canonical_json(r) for r in aux))
    return module, root, run


def test_chapters_use_complete_data_and_explicitly_unprovided_reviewer_details(tmp_path, monkeypatch):
    module, root, run = fixture(tmp_path, monkeypatch)
    out = run / "thesis";module.build_thesis(root, run, out)
    assert "[diisi peneliti]" in (out / "BAB_IV.md").read_text()
    text = (out / "BAB_V.md").read_text()
    assert "synthetic-only-not-a-research-result" in text and "0.00" in text
    assert "tidak tersedia" in text and (out / "LAMPIRAN_SCHEMA.md").is_file()
    assert len(json.loads((out / "source-and-output-hashes.json").read_bytes())["files"]) >= 5


def test_chapters_reject_missing_auxiliary_results_instead_of_claiming_robustness(tmp_path, monkeypatch):
    module, root, run = fixture(tmp_path, monkeypatch)
    path = run / "auxiliary/outcomes.jsonl";lines = path.read_bytes().splitlines(keepends=True);path.write_bytes(b"".join(lines[:-1]))
    with pytest.raises(ValueError, match="4800auxiliary"):
        module.build_thesis(root, run, run / "thesis")
    assert not (run / "thesis/BAB_V.md").exists()
