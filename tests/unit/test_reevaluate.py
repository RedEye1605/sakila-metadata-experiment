import json

import pytest

from sakila_experiment.annotations import CRITERIA, consolidate, rows
from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.evaluation.reevaluate import generation_signature, validate_adjudication
from sakila_experiment.evaluation.reevaluate import validate_reference_changes
from sakila_experiment.contracts import GoldReference, load_questions
from test_annotations import annotation_fixture, rewrite


def test_reference_only_reevaluation_requires_bound_complete_human_records(tmp_path):
    package, _ = annotation_fixture(tmp_path)
    inputs = json.loads((package / "manifest.json").read_bytes())["source_input_sha256"]
    manifest = {"questions_sha256": inputs["data/public/main.questions.jsonl"], "gold_sha256": inputs["data/private/main.gold.jsonl"],
                "model_version_or_hash": "m", "inference_config": {}, "prompt_template_sha256": "p", "database_schema_sha256": "s",
                "database_data_sha256": "d", "snapshots": {"snapshot_sha256": {"S0": "s0"}}}
    gold = tmp_path / "corrected.jsonl"; gold.write_text("synthetic replacement reference\n")
    for reviewer in ("A01", "A02"):
        for kind, criteria in CRITERIA.items():
            path = tmp_path / reviewer / (kind + ".csv"); data = rows(path)
            for row in data:
                row.update({c: "yes" for c in criteria}); row.update(decision="accepted", annotated_at_utc="2026-10-27T10:00:00Z")
            rewrite(path, data)
    output = tmp_path / "consolidated"
    consolidate(package, tmp_path / "A01", tmp_path / "A02", output)
    adjudication = output / "adjudication.csv"; adjudication.chmod(0o644)
    receipt = {"status": "adjudicated", "reviewers": ["A01", "A02"], "adjudicator": "synthetic-test-only", "adjudicated_at_utc": "2026-10-27T12:00:00Z",
               "generation_signature": generation_signature(manifest), "gold_sha256": sha256_bytes(gold.read_bytes()),
               "consolidation_report_sha256": sha256_bytes((output / "report.json").read_bytes()),
               "review_package_sha256": sha256_bytes((package / "manifest.json").read_bytes()), "adjudication_sha256": sha256_bytes(adjudication.read_bytes())}
    with pytest.raises(ValueError, match="final human"):
        validate_adjudication(manifest, receipt, gold, package, adjudication)
    data = rows(adjudication)
    for row in data:
        row.update(final_decision="accepted", adjudicator="synthetic-test-only", rationale="Synthetic validation case", adjudicated_at_utc="2026-10-27T12:00:00Z")
    rewrite(adjudication, data); receipt["adjudication_sha256"] = sha256_bytes(adjudication.read_bytes())
    validate_adjudication(manifest, receipt, gold, package, adjudication)
    receipt["adjudication_sha256"] = "bad"
    with pytest.raises(ValueError, match="receipt"):
        validate_adjudication(manifest, receipt, gold, package, adjudication)
    receipt["adjudication_sha256"] = sha256_bytes(adjudication.read_bytes())
    template = package / "A01/questions.csv"
    template.chmod(0o644); template.write_text("Accidentally edited distributed template")
    with pytest.raises(ValueError, match="template changed"):
        validate_adjudication(manifest, receipt, gold, package, adjudication)


def test_unrecorded_gold_edit_and_changed_complexity_cannot_enter_rescore(tmp_path):
    package, _ = annotation_fixture(tmp_path)
    questions = load_questions(tmp_path / "data/public/main.questions.jsonl")
    decisions = [{"item_id": "questions:Q001", "final_decision": "accepted", "final_correction": ""}]
    gold = {"Q001": GoldReference(question_id="Q001", sql="SELECT 1", column_count=1, review_status="approved")}
    validate_reference_changes(package, decisions, gold, questions)
    gold["Q001"] = gold["Q001"].model_copy(update={"sql": "SELECT 2"})
    with pytest.raises(ValueError, match="adjudicated correction"):
        validate_reference_changes(package, decisions, gold, questions)
    decisions[0].update(final_decision="accepted_with_correction", final_correction=json.dumps({"gold_sql": "SELECT 2"}))
    validate_reference_changes(package, decisions, gold, questions)
    sql = "SELECT COUNT(*) FROM actor JOIN film_actor USING(actor_id)"
    decisions[0]["final_correction"] = json.dumps({"gold_sql": sql})
    gold["Q001"] = gold["Q001"].model_copy(update={"sql": sql})
    with pytest.raises(ValueError, match="complexity"):
        validate_reference_changes(package, decisions, gold, questions)


def test_stored_results_are_rescored_without_http_or_ledger_mutation(tmp_path, monkeypatch):
    """Synthetic orchestration fixture; actual review/audit guards tested above."""
    from sakila_experiment.config import AppConfig, InferenceConfig
    from sakila_experiment.db.execute import ResultTable, QueryExecution
    from sakila_experiment.evaluation import reevaluate as module
    import httpx

    config = AppConfig(project_root=tmp_path, inference=InferenceConfig(model_id="synthetic"))
    source = tmp_path / "original"; (source / "results").mkdir(parents=True)
    (source / "ledger.sqlite3").write_bytes(b"synthetic immutable ledger")
    (tmp_path / "prompts").mkdir(); (tmp_path / "prompts/generation.txt").write_text("Synthetic prompt")
    questions = tmp_path / "questions.jsonl"
    questions.write_bytes(b"".join(canonical_json({"question_id": f"Q{i+1:03}", "question": f"Pertanyaan sintetis nomor {i+1} untuk pengujian?", "complexity": c}) for i, c in enumerate(("simple", "medium", "complex"))))
    gold_path = tmp_path / "reviewed.jsonl"
    gold_path.write_bytes(b"".join(canonical_json({"question_id": f"Q{i+1:03}", "sql": "SELECT 2", "column_count": 1, "review_status": "approved"}) for i in range(3)))
    receipt = tmp_path / "receipt.json"; receipt.write_text("{}")
    snapshots = {s: s for s in ("S0", "S1", "S2", "S3")}
    manifest = {"mode": "preliminary", "experiment_id": "synthetic", "questions_sha256": sha256_bytes(questions.read_bytes()),
                "model_version_or_hash": "m", "inference_config": config.inference.model_dump(mode="json"),
                "prompt_template_sha256": sha256_bytes((tmp_path / "prompts/generation.txt").read_bytes()),
                "database_schema_sha256": "s", "database_data_sha256": "d", "snapshots": {"snapshot_sha256": snapshots},
                "experiment_config": {"analysis_seed": 20261029}}
    (source / "manifest.json").write_bytes(canonical_json(manifest))
    predicted = ResultTable(("value",), (3,), ((1,),))
    corrected = ResultTable(("value",), (3,), ((2,),))
    records = []
    for q in load_questions(questions):
        for s in snapshots:
            for repetition in range(1, 6):
                trial = q.question_id + "-" + s + "-r" + str(repetition)
                (source / "results" / (trial + ".json")).write_bytes(canonical_json(predicted.encoded()))
                records.append({"trial_id": trial, "question_id": q.question_id, "scenario_id": s, "repetition_id": repetition,
                                "complexity": q.complexity, "execution_status": "success", "execution_accuracy": 1,
                                "extracted_sql": "SELECT 1", "inference_latency_ms": 1, "sql_execution_latency_ms": 1, "input_tokens": 10, "output_tokens": 3})
    monkeypatch.setattr(module, "audit_run", lambda _: (manifest, records))
    monkeypatch.setattr(module, "validate_adjudication", lambda *a: [])
    monkeypatch.setattr(module, "validate_reference_changes", lambda *a: None)
    monkeypatch.setattr(module, "validate_fixed_evaluation", lambda *a: None)
    monkeypatch.setattr(module, "validate_scenario_set", lambda _: {"snapshot_sha256": snapshots})
    monkeypatch.setattr(module, "inspect_database", lambda _: {"schema_sha256": "s", "data_sha256": "d", "technical_schema": {"tables": [{"name": "actor"}]}})
    monkeypatch.setattr(module, "execute_sql", lambda *a: QueryExecution("success", "accepted", corrected, sha256_bytes(canonical_json(corrected.encoded())), 1))
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: pytest.fail("Reference reevaluation must not call inference or HTTP"))
    output = tmp_path / "rescored"
    result = module.reevaluate(config, source, gold_path, questions, tmp_path / "snapshots", receipt, output,
                               review_package=tmp_path / "review", adjudication_file=tmp_path / "adjudication.csv")
    assert result["generation_requests"] == 0 and result["original_generation_mode"] == "preliminary"
    rows_out = [json.loads(line) for line in (output / "trials.jsonl").read_bytes().splitlines()]
    assert all(r["source_execution_accuracy"] == 1 and r["execution_accuracy"] == 0 for r in rows_out)
    assert (source / "ledger.sqlite3").read_bytes() == b"synthetic immutable ledger"


def test_reference_only_rescore_rejects_execution_or_comparator_drift(tmp_path):
    from sakila_experiment.config import AppConfig
    from sakila_experiment.evaluation.reevaluate import validate_fixed_evaluation, FIXED_EVALUATOR_FILES
    from sakila_experiment.evaluation.compare import COMPARATOR_VERSION
    config = AppConfig(project_root=tmp_path)
    files = []
    for name in (*FIXED_EVALUATOR_FILES, "docs/analysis-plan.md"):
        path = tmp_path / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"synthetic fixed source")
        files.append({"path": name, "sha256": sha256_bytes(path.read_bytes())})
    manifest = {"database_config": config.database.model_dump(mode="json"), "comparator_version": COMPARATOR_VERSION,
                "analysis_protocol_sha256": files[-1]["sha256"], "source_version": {"source_files": files}}
    validate_fixed_evaluation(config, manifest)
    manifest["database_config"]["time_zone"] = "+07:00"
    with pytest.raises(ValueError, match="execution/comparison policy"):
        validate_fixed_evaluation(config, manifest)
    manifest["database_config"] = config.database.model_dump(mode="json")
    (tmp_path / FIXED_EVALUATOR_FILES[0]).write_bytes(b"changed comparison")
    with pytest.raises(ValueError, match="implementation changed"):
        validate_fixed_evaluation(config, manifest)
