"""Replay frozen predictions on a separate fixture clone without inference.

Primary EX is never overwritten. Every assigned prediction, including primary
failures, is included in each predeclared auxiliary case. Responses are never
repaired. Administrative setup is confined to evaluation.fixtures.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from ..analysis.report import audit_run
from ..artifacts import canonical_json, publish_artifact, sha256_bytes
from ..contracts import load_gold
from ..db.execute import execute_sql
from ..db.inspect import inspect_database, verify_fingerprint
from ..experiment.runner import source_version
from ..instrument import read_manifest
from .compare import compare_results, comparison_spec
from .fixtures import prepare_fixture


class RobustnessError(RuntimeError):
    pass


def score_prediction(config, tables, record, reference, gold_execution):
    """Score the exact mechanically extracted SQL, never dispatch a model."""
    sql = record.get("extracted_sql")
    if sql is None:
        return {"execution_status": "invalid_model_output", "execution_accuracy": 0,
                "execution_result_hash": None, "comparison_reason": "no_SQL_from_original_response"}, None
    result = execute_sql(config, sql, tables)
    if result.status == "infrastructure_error":
        raise RobustnessError("Auxiliary SQL infrastructure failure; no EX outcome assigned")
    outcome = {"execution_status": result.status, "execution_result_hash": result.result_sha256,
               "error_code": result.error_code, "error_message": result.error_message,
               "sql_execution_latency_ms": result.latency_ms}
    if result.status != "success":
        return {**outcome, "execution_accuracy": 0, "comparison_reason": "SQL_rejected_or_failed"}, None
    spec = comparison_spec(reference)
    comparison = compare_results(result.result, gold_execution.result, spec)
    return {**outcome, "execution_accuracy": comparison.execution_accuracy, "comparison_reason": comparison.reason,
            "column_order_policy": reference.column_order, "column_permutation": comparison.column_permutation}, result.result


def replay_fixtures(config, run_directory: Path, output: Path, *, progress=print):
    root = config.project_root
    manifest, records = audit_run(run_directory)
    if (manifest.get("mode") not in {"preliminary", "main"} or not config.benchmark_manifest
            or manifest.get("benchmark_manifest_sha256") != sha256_bytes(config.resolve(config.benchmark_manifest).read_bytes())):
        raise RobustnessError("Auxiliary replay requires the complete matching revision-02 exploratory benchmark")
    instrument, paths = read_manifest(root, config.resolve(config.benchmark_manifest))
    from ..instrument import validate_instrument
    validate_instrument(root, config.resolve(config.benchmark_manifest))
    gold = load_gold(paths["gold"])
    if manifest.get("comparator_version") != instrument.result_comparison:
        raise RobustnessError("Auxiliary comparator differs from the frozen generation run")
    expected_order = "permutation" if instrument.result_comparison == "ex-results-v3-column-permutation" else "fixed"
    if any(reference.column_order != expected_order for reference in gold.values()):
        raise RobustnessError("Auxiliary gold column policy differs from the frozen comparator")
    fixture_bytes = paths["fixture_specification"].read_bytes()
    fixture_definition = json.loads(fixture_bytes)
    if paths["fixture_specification"].resolve() not in {(root / f"research/{version}/fixture_cases.json").resolve() for version in ("revision-02", "revision-03")}:
        raise RobustnessError("Fixture builder requires a versioned research definition")
    cases = [case["fixture_id"] for case in fixture_definition["cases"]]
    if len(cases) != 8 or len(set(cases)) != 8:
        raise RobustnessError("Expected the eight predeclared distinct fixture cases")
    baseline = json.loads((root / "runs/database/baseline.json").read_bytes())
    tables = frozenset(table["name"] for table in baseline["technical_schema"]["tables"])
    verify_fingerprint(inspect_database(config), baseline)
    frozen = {"status": "auxiliary_plan_frozen", "benchmark_id": instrument.benchmark_id,
              "comparator_version": instrument.result_comparison,
              "source_run_manifest_sha256": sha256_bytes((run_directory / "manifest.json").read_bytes()),
              "source_trials_sha256": sha256_bytes((run_directory / "trials.jsonl").read_bytes()),
              "benchmark_manifest_sha256": manifest["benchmark_manifest_sha256"],
              "fixture_specification_sha256": sha256_bytes(fixture_bytes), "case_ids": cases,
              "trial_ids": [record["trial_id"] for record in records], "generation_requests": 0,
              "scope": "all600assignedSQL_on_all8auxiliarycases; primary EX unchanged",
              "source_version": source_version(root),
              "human_review_complete": manifest.get("human_review_status") == "user_attested_complete",
              "review_basis": "user_attestation" if manifest.get("human_review_status") == "user_attested_complete" else "not_provided",
              "reviewer_identity_status": manifest.get("reviewer_identity_status", "not_recorded"), "public_results_embargo": True}
    publish_artifact(output / "plan.json", canonical_json(frozen))
    outcomes = []
    try:
        for case in cases:
            folder = output / case
            pending = [r for r in records if not (folder / "outcomes" / (r["trial_id"] + ".json")).is_file()]
            selected, gold_results = None, {}
            if pending:
                receipts = folder / "preparation-attempts"
                attempt = len(list(receipts.glob("*.json"))) + 1
                selected, fixture_receipt = prepare_fixture(root, case, receipts / f"{attempt:04}.json", definition=paths["fixture_specification"])
                selected = selected.model_copy(update={"database": selected.database.model_copy(update={
                    "sql_policy_version": config.database.sql_policy_version, "time_names_locale": config.database.time_names_locale})})
                for qid, reference in gold.items():
                    execution = execute_sql(selected, reference.sql, tables)
                    if execution.status != "success":
                        raise RobustnessError("Gold execution failed on the predefined fixture: " + case + "/" + qid)
                    spec = comparison_spec(reference)
                    if not compare_results(execution.result, execution.result, spec).execution_accuracy:
                        raise RobustnessError("Gold result contract failed on fixture")
                    publish_artifact(folder / "gold-results" / (qid + ".json"), canonical_json(execution.result.encoded()))
                    gold_results[qid] = execution
            for record in records:
                path = folder / "outcomes" / (record["trial_id"] + ".json")
                binding = {"trial_id": record["trial_id"], "question_id": record["question_id"], "scenario_id": record["scenario_id"],
                           "comparator_version": instrument.result_comparison,
                           "repetition_id": record["repetition_id"], "fixture_id": case,
                           "sql_sha256": sha256_bytes(canonical_json(record.get("extracted_sql"))),
                           "gold_sql_sha256": sha256_bytes(gold[record["question_id"]].sql.encode()),
                           "source_run_manifest_sha256": frozen["source_run_manifest_sha256"],
                           "fixture_specification_sha256": frozen["fixture_specification_sha256"]}
                if path.exists():
                    outcome = json.loads(path.read_bytes())
                    if any(outcome.get(key) != value for key, value in binding.items()):
                        raise RobustnessError("Stored auxiliary outcome input differs from the frozen replay")
                    if type(outcome.get("execution_accuracy")) is not int or outcome["execution_accuracy"] not in {0, 1}:
                        raise RobustnessError("Stored auxiliary outcome is not evaluable")
                else:
                    score, result = score_prediction(selected, tables, record, gold[record["question_id"]], gold_results[record["question_id"]])
                    if result is not None:
                        publish_artifact(folder / "results" / (record["trial_id"] + ".json"), canonical_json(result.encoded()))
                    outcome = {**binding, **score, "fixture_data_sha256": fixture_receipt["database_data_sha256"],
                               "gold_result_hash": gold_results[record["question_id"]].result_sha256, "generation_requests": 0}
                    publish_artifact(path, canonical_json(outcome))
                if outcome.get("execution_result_hash") is not None:
                    if sha256_bytes((folder / "results" / (record["trial_id"] + ".json")).read_bytes()) != outcome["execution_result_hash"]:
                        raise RobustnessError("Auxiliary result artifact changed")
                if sha256_bytes((folder / "gold-results" / (record["question_id"] + ".json")).read_bytes()) != outcome["gold_result_hash"]:
                    raise RobustnessError("Auxiliary gold result artifact changed")
                outcomes.append(outcome)
            publish_artifact(folder / "outcome-hashes.json", canonical_json({r["trial_id"]: sha256_bytes((folder / "outcomes" / (r["trial_id"] + ".json")).read_bytes()) for r in records}))
            progress(canonical_json({"fixture_id": case, "auxiliary_trials": len(records), "generation_requests": 0}).decode().strip())
    except Exception as error:
        incidents = output / "incidents"
        number = len(list(incidents.glob("*.json"))) + 1
        publish_artifact(incidents / f"{number:04}.json", canonical_json({
            "fixture_id": case, "error_type": type(error).__name__, "error_message": str(error),
            "execution_accuracy": None, "generation_requests": 0, "stored_outcomes_preserved": True}))
        raise
    finally:
        verify_fingerprint(inspect_database(config), baseline)
    scenario_cases = defaultdict(list)
    trial_scores = defaultdict(list)
    for row in outcomes:
        scenario_cases[row["scenario_id"], row["fixture_id"]].append(row["execution_accuracy"])
        trial_scores[row["trial_id"]].append(row["execution_accuracy"])
    if len(outcomes) != len(cases) * len(records) or any(len(scores) != 8 for scores in trial_scores.values()):
        raise RobustnessError("Auxiliary replay is incomplete")
    by_scenario = []
    for scenario in ("S0", "S1", "S2", "S3"):
        selected_records = [r for r in records if r["scenario_id"] == scenario]
        correct = sum(all(trial_scores[r["trial_id"]]) for r in selected_records)
        by_scenario.append({"scenario_id": scenario, "trials": len(selected_records), "all_auxiliary_cases_correct": correct,
                            "all_auxiliary_cases_percent": correct / len(selected_records) * 100})
    report = {"status": "auxiliary_replay_complete", "generation_requests": 0,
              "review_status": manifest.get("human_review_status", "pending"),
              "reviewer_identity_status": manifest.get("reviewer_identity_status", "not_recorded"),
              "primary_database_unchanged": True, "primary_EX_modified": False,
              "by_scenario": by_scenario,
              "by_case": [{"scenario_id": scenario, "fixture_id": case, "trials": len(scores), "correct": sum(scores),
                           "auxiliary_accuracy_percent": sum(scores) / len(scores) * 100} for (scenario, case), scores in sorted(scenario_cases.items())],
              "limits": "Finite schema-valid constructed witnesses are not proofs of universal semantic equivalence or independently sampled databases."}
    publish_artifact(output / "outcomes.jsonl", b"".join(canonical_json(row) for row in outcomes))
    publish_artifact(output / "report.json", canonical_json(report))
    return report
