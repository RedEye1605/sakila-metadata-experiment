import json
from dataclasses import replace
from pathlib import Path

import pytest

from sakila_experiment.artifacts import canonical_json, sha256_bytes
from sakila_experiment.config import AppConfig, ExperimentConfig, InferenceConfig
from sakila_experiment.contracts import GoldReference, Question
from sakila_experiment.db.execute import QueryExecution, ResultTable
from sakila_experiment.experiment import runner
from sakila_experiment.experiment.ledger import Ledger
from sakila_experiment.experiment.schedule import build_schedule
from sakila_experiment.generation.llama import BackendEvidence, CheckedPrompt, GenerationResponse


def setup_pilot(tmp_path, monkeypatch):
    root = tmp_path / "project"
    (root / "runs/database").mkdir(parents=True)
    baseline = {"technical_schema": {"tables": [{"name": "actor"}]}, "schema_sha256": "schema", "ddl_sha256": "ddl", "data_sha256": "data", "server": {}}
    (root / "runs/database/baseline.json").write_bytes(canonical_json(baseline))
    (root / "prompts").mkdir()
    (root / "prompts/generation.txt").write_text("Generate one MySQL SELECT query.")
    snapshots = tmp_path / "snapshots"
    payload = {"technical_schema": {"tables": [{"name": "actor"}]}, "descriptions": [], "business_context": []}
    for scenario in ("S0", "S1", "S2", "S3"):
        folder = snapshots / scenario
        folder.mkdir(parents=True)
        (folder / "payload.json").write_bytes(canonical_json(payload))
        (folder / "manifest.json").write_bytes(canonical_json({"snapshot_id": scenario, "payload_file": "payload.json", "snapshot_sha256": sha256_bytes(canonical_json(payload))}))
    question = Question(question_id="P001", question="Berapa jumlah aktor untuk fixture?", complexity="simple")
    reference = GoldReference(question_id="P001", sql="SELECT COUNT(*) FROM actor", column_count=1)
    assignments = build_schedule((question,), ExperimentConfig(), pilot=True)
    config = AppConfig(project_root=root, inference=InferenceConfig(model_id="fixture"))
    evidence = BackendEvidence("fixture", "a" * 64, "fixture", 16384, "b" * 64)
    manifest = {"mode": "pilot", "fixed": True, "snapshot_manifest_sha256": {s: sha256_bytes((snapshots / s / "manifest.json").read_bytes()) for s in ("S0", "S1", "S2", "S3")},
                "prompt_template_sha256": sha256_bytes((root / "prompts/generation.txt").read_bytes())}
    monkeypatch.setattr(runner, "pilot_inputs", lambda *a, **k: (manifest.copy(), assignments, {"P001": question}, {"P001": reference}))
    monkeypatch.setattr(runner, "load_backend_evidence", lambda p: (evidence, {}))
    monkeypatch.setattr(runner, "inspect_database", lambda c: baseline)
    result = ResultTable(("count",), (3,), ((200,),))
    success = QueryExecution("success", "accepted", result, sha256_bytes(canonical_json(result.encoded())), 1.0)
    monkeypatch.setattr(runner, "execute_sql", lambda *a: success)
    calls = []
    response = GenerationResponse({"choices": [{"message": {"content": reference.sql}}]}, reference.sql, "stop", 10, 5, "api_usage", 1.0, True)
    class FakeClient:
        def __init__(self, *args): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def prepare(self, prompt):
            assert all(reference.sql not in m["content"] for m in prompt.chat_messages())
            return CheckedPrompt(prompt, 10, evidence)
        def generate(self, prompt, seed):
            calls.append(seed)
            return response
    monkeypatch.setattr(runner, "LlamaClient", FakeClient)
    return config, snapshots, assignments, reference, success, response, calls


def test_end_to_end_pilot_durable_log_and_resume_never_duplicate_generation(tmp_path, monkeypatch):
    config, snapshots, assignments, reference, success, response, calls = setup_pilot(tmp_path, monkeypatch)
    output = tmp_path / "output"
    result = runner.run_pilot(config, snapshots, Path("unused"), output, "fixture", progress=lambda x: None)
    assert result["completed_trials"] == 4
    assert len(calls) == 4
    runner.run_pilot(config, snapshots, Path("unused"), output, "fixture", progress=lambda x: None)
    assert len(calls) == 4
    records = [json.loads(line) for line in (output / "trials.jsonl").read_text().splitlines()]
    assert all(r["execution_accuracy"] == 1 for r in records)
    assert all(r["snapshot_sha256"] and r["gold_result_hash"] and r["prompt_hash"] for r in records)


def test_evaluation_outage_preserves_response_and_resume_only_evaluates(tmp_path, monkeypatch):
    config, snapshots, assignments, reference, success, response, calls = setup_pilot(tmp_path, monkeypatch)
    evaluate = runner.evaluate_response
    def outage(*args): raise runner.RunError("fixture database outage")
    monkeypatch.setattr(runner, "evaluate_response", outage)
    output = tmp_path / "output"
    with pytest.raises(runner.RunError, match="interrupted"):
        runner.run_pilot(config, snapshots, Path("unused"), output, "fixture", progress=lambda x: None)
    assert len(calls) == 1
    with Ledger(output / "ledger.sqlite3") as ledger:
        assert ledger.completed("fixture") == {}
        assert ledger.latest_response("fixture", assignments[0].trial_id) is not None
    monkeypatch.setattr(runner, "evaluate_response", evaluate)
    runner.run_pilot(config, snapshots, Path("unused"), output, "fixture", progress=lambda x: None)
    assert len(calls) == 4


def test_post_completion_observer_failure_preserves_terminal_without_regeneration(tmp_path, monkeypatch):
    config, snapshots, assignments, _, _, _, calls = setup_pilot(tmp_path, monkeypatch)
    output = tmp_path / "observer-failure"
    def observer(_):
        raise runner.RunError("synthetic sampler observation unavailable")
    with pytest.raises(runner.RunError, match="sampler observation"):
        runner.run_pilot(config, snapshots, Path("unused"), output, "fixture", progress=observer)
    with Ledger(output / "ledger.sqlite3") as ledger:
        assert set(ledger.completed("fixture")) == {assignments[0].trial_id}
        assert ledger.connection.execute("SELECT count(*) FROM events WHERE kind='infrastructure_failure'").fetchone()[0] == 0
    assert len(calls) == 1
    runner.run_pilot(config, snapshots, Path("unused"), output, "fixture", progress=lambda _: None)
    assert len(calls) == 4


def test_infrastructure_is_never_ex_zero_but_invalid_model_output_is(tmp_path, monkeypatch):
    config, snapshots, assignments, reference, success, response, calls = setup_pilot(tmp_path, monkeypatch)
    invalid = replace(response, text="", response_valid=False)
    outcome, result = runner.evaluate_response(config, frozenset({"actor"}), invalid, reference, success)
    assert outcome["execution_accuracy"] == 0 and result is None
    monkeypatch.setattr(runner, "execute_sql", lambda *a: QueryExecution("infrastructure_error", "accepted", error_message="outage"))
    with pytest.raises(runner.RunError):
        runner.evaluate_response(config, frozenset({"actor"}), response, reference, success)


def test_dry_run_does_not_generate_or_register_attempts(tmp_path, monkeypatch):
    config, snapshots, assignments, reference, success, response, calls = setup_pilot(tmp_path, monkeypatch)
    output = tmp_path / "output"
    report = runner.run_pilot(config, snapshots, Path("unused"), output, "fixture", dry_run=True)
    assert report["generation_requests"] == 0 and not calls
    assert not (output / "ledger.sqlite3").exists()


def test_prompt_mutation_mid_run_stops_before_another_generation(tmp_path, monkeypatch):
    config, snapshots, assignments, reference, success, response, calls = setup_pilot(tmp_path, monkeypatch)
    client_type = runner.LlamaClient
    generate = client_type.generate
    def mutate(self, prompt, seed):
        result = generate(self, prompt, seed)
        (config.project_root / "prompts/generation.txt").write_text("A changed instruction must not enter the next trial.")
        return result
    monkeypatch.setattr(client_type, "generate", mutate)
    with pytest.raises(runner.RunError, match="template changed"):
        runner.run_pilot(config, snapshots, Path("unused"), tmp_path / "output", "fixture", progress=lambda x: None)
    assert len(calls) == 1


def test_main_draft_gate_stops_before_backend_or_generation(tmp_path, monkeypatch):
    from sakila_experiment.experiment import readiness
    monkeypatch.setattr(readiness, "main_readiness", lambda *a: {"status": "blocked", "blockers": ["Main gold semantic review is still draft"]})
    def forbidden(*args, **kwargs):
        pytest.fail("Blocked main inputs must never reach model preparation")
    monkeypatch.setattr(runner, "_build_inputs", forbidden)
    with pytest.raises(runner.RunError, match="still draft"):
        runner.run_main(AppConfig(), tmp_path, tmp_path / "backend.json", tmp_path / "main", "main", tmp_path / "pilot", freeze_only=True)
    assert not (tmp_path / "main").exists()


def test_main_requires_separate_freeze_receipt_and_freeze_never_generates(tmp_path, monkeypatch):
    config, snapshots, assignments, reference, success, response, calls = setup_pilot(tmp_path, monkeypatch)
    def reviewed_inputs(*args):
        manifest, plan, questions, references = runner.pilot_inputs(config, snapshots, Path("unused"))
        manifest.update(mode="main", main_experiment_allowed=True)
        return manifest, plan, questions, references
    monkeypatch.setattr(runner, "main_inputs", reviewed_inputs)
    output = tmp_path / "synthetic-main-gate"
    with pytest.raises(runner.RunError, match="Freeze"):
        runner.run_main(config, snapshots, Path("unused"), output, "synthetic", tmp_path / "pilot")
    assert not calls
    receipt = runner.run_main(config, snapshots, Path("unused"), output, "synthetic", tmp_path / "pilot", freeze_only=True)
    assert receipt["generation_requests"] == 0 and not calls
    assert (output / "freeze.json").is_file()
    result = runner.run_main(config, snapshots, Path("unused"), output, "synthetic", tmp_path / "pilot", progress=lambda x: None)
    assert result["status"] == "main_complete" and len(calls) == 4


def test_600_synthetic_assignments_survive_outage_and_explicit_crash_recovery(tmp_path, monkeypatch):
    """Synthetic isolated fixtures only; never call a real model or main data."""
    from sakila_experiment.evaluation.safety import validate_sql
    from sakila_experiment.experiment.ledger import LedgerError
    config, snapshots, _, _, success, response, _ = setup_pilot(tmp_path, monkeypatch)
    questions = {f"Q{i:03}": Question(question_id=f"Q{i:03}", question=f"Berapa nilai sintetis untuk fixture nomor {i}?", complexity=("simple", "medium", "complex")[(i - 1) // 10]) for i in range(1, 31)}
    references = {q: GoldReference(question_id=q, sql="SELECT COUNT(*) FROM actor", column_count=1, review_status="approved") for q in questions}
    plan = build_schedule(tuple(questions.values()), ExperimentConfig())
    base = runner.pilot_inputs(config, snapshots, Path("unused"))[0]
    manifest = {**base, "mode": "main", "main_experiment_allowed": True, "synthetic_fixture": True}
    monkeypatch.setattr(runner, "main_inputs", lambda *a: (manifest.copy(), plan, questions, references))
    generated = []
    class SyntheticCrash(RuntimeError): pass
    class Client:
        def __init__(self, *args): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def prepare(self, prompt): return CheckedPrompt(prompt, 10, BackendEvidence("fixture", "a" * 64, "fixture", 16384, "b" * 64))
        def generate(self, checked, seed):
            generated.append(seed)
            if len(generated) == 202:
                raise SyntheticCrash("simulated process exit with no durable response")
            sql = ("SELECT COUNT(*) FROM actor", "SELECT 0", "DROP TABLE actor", "SELECT missing_column FROM actor")[len(generated) % 4]
            return replace(response, text=sql, raw_response={"synthetic_fixture": True, "sql": sql})
    monkeypatch.setattr(runner, "LlamaClient", Client)
    outage = [False]
    def execute(config, sql, tables):
        if sql == "SELECT COUNT(*) FROM actor":
            return success
        if len(generated) == 73 and not outage[0]:
            outage[0] = True
            return QueryExecution("infrastructure_error", "accepted", error_code=2003)
        validation = validate_sql(sql, tables)
        if not validation.accepted:
            return QueryExecution("rejected", validation.code)
        if "missing_column" in sql:
            return QueryExecution("model_error", "accepted", error_code=1054)
        return QueryExecution("success", "accepted", ResultTable(("zero",), (3,), ((0,),)), "e" * 64, 1.0)
    monkeypatch.setattr(runner, "execute_sql", execute)
    directory = tmp_path / "synthetic-600"
    def run(**kwargs):
        return runner.run_main(config, snapshots, Path("unused"), directory, "synthetic-600", tmp_path / "pilot", progress=lambda x: None, **kwargs)
    run(freeze_only=True)
    with pytest.raises(runner.RunError, match="infrastructure"):
        run()
    assert len(generated) == 73
    with pytest.raises(SyntheticCrash):
        run()
    assert len(generated) == 202
    with pytest.raises(LedgerError, match="ambiguous"):
        run()
    assert len(generated) == 202
    with Ledger(directory / "ledger.sqlite3") as ledger:
        row = ledger.connection.execute("SELECT trial_id,attempt_id FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        ledger.recover_dispatch("synthetic-600", row[0], row[1], operator="Synthetic test operator", note="Synthetic crashed process is stopped; no response exists")
    completed = run()
    assert completed["completed_trials"] == 600 and len(generated) == 601
    run()
    assert len(generated) == 601
    with Ledger(directory / "ledger.sqlite3") as ledger:
        outcomes = ledger.completed("synthetic-600")
        assert len(outcomes) == 600
        assert all(type(row["execution_accuracy"]) is int for row in outcomes.values())
        assert ledger.connection.execute("SELECT COUNT(*) FROM events WHERE kind='infrastructure_failure'").fetchone()[0] == 2
